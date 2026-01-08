import logging
import re
from urllib.parse import quote

from playwright.async_api import TimeoutError as PlaywrightTimeout

from app.scrapers.base import BaseScraper
from app.schemas import ProductCandidate
from app.config import settings

logger = logging.getLogger(__name__)


class ShufersalScraper(BaseScraper):
    """Scraper for Shufersal Online."""

    BASE_URL = "https://www.shufersal.co.il"
    SEARCH_URL = "https://www.shufersal.co.il/online/he/search?text={query}"

    def get_store_id(self) -> str:
        return "shufersal"

    def get_store_name(self) -> str:
        return "Shufersal"

    async def search(self, query: str) -> list[ProductCandidate]:
        """Search for products on Shufersal."""
        products = []
        page = None

        try:
            page = await self._create_page()
            search_url = self.SEARCH_URL.format(query=quote(query))
            logger.info(f"Searching Shufersal for: {query}")

            # Use domcontentloaded and wait for content - networkidle times out
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)

            # Wait for product tiles to load
            try:
                await page.wait_for_selector("li[data-product-code]", timeout=15000)
            except PlaywrightTimeout:
                logger.warning(f"No products found for query: {query}")
                return []

            # Extract product data - use li elements with data attributes
            product_elements = await page.query_selector_all("li[data-product-code][data-product-name]")
            seen_ids = set()

            for i, element in enumerate(product_elements):
                if len(products) >= settings.scraper_max_results:
                    break
                try:
                    product = await self._extract_product(element)
                    if product and product.id not in seen_ids:
                        products.append(product)
                        seen_ids.add(product.id)
                except Exception as e:
                    logger.warning(f"Failed to extract product {i}: {e}")
                    continue

            logger.info(f"Found {len(products)} products for: {query}")

        except Exception as e:
            logger.error(f"Shufersal search failed for '{query}': {e}")
        finally:
            if page:
                await page.close()
            await self._delay()

        return products

    async def _extract_product(self, element) -> ProductCandidate | None:
        """Extract product data from a product tile element using data attributes."""
        try:
            # Get product code from data attribute
            external_id = await element.get_attribute("data-product-code")
            if not external_id:
                return None

            # Get product name from data attribute
            name = await element.get_attribute("data-product-name")
            if not name:
                return None

            # Get price from data attribute
            price_str = await element.get_attribute("data-product-price")
            if not price_str:
                return None
            try:
                price = float(price_str)
            except ValueError:
                return None

            # Get product URL
            url = None
            link_elem = await element.query_selector("a[href*='/p/']")
            if link_elem:
                href = await link_elem.get_attribute("href")
                if href:
                    url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

            # Get image URL
            image_url = None
            img_elem = await element.query_selector("img")
            if img_elem:
                image_url = await img_elem.get_attribute("src")
                if image_url and not image_url.startswith("http"):
                    image_url = f"{self.BASE_URL}{image_url}"

            # Get size descriptor from brand-name section (e.g., "200 גרם" or "מחיר לפי משקל")
            size_descriptor = None
            size_elem = await element.query_selector(".brand-name span:first-child")
            if size_elem:
                size_descriptor = (await size_elem.inner_text()).strip()

            return self._make_product_candidate(
                external_id=external_id,
                name=name,
                price=price,
                url=url,
                image_url=image_url,
                size_descriptor=size_descriptor,
            )

        except Exception as e:
            logger.debug(f"Error extracting product: {e}")
            return None

    def _parse_price(self, price_text: str) -> float | None:
        """Parse price from text, handling Hebrew currency format."""
        if not price_text:
            return None

        # Remove currency symbols and whitespace
        cleaned = price_text.replace("₪", "").replace("ש\"ח", "").strip()

        # Extract number (handle both . and , as decimal separator)
        match = re.search(r"(\d+[.,]?\d*)", cleaned)
        if match:
            price_str = match.group(1).replace(",", ".")
            try:
                return float(price_str)
            except ValueError:
                return None
        return None
