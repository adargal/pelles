import json
import logging
import re
from pathlib import Path
from urllib.parse import quote

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout, async_playwright

from app.scrapers.base import BaseScraper
from app.schemas import ProductCandidate
from app.config import settings

logger = logging.getLogger(__name__)

# Path to store session cookies after CAPTCHA is solved
COOKIES_FILE = Path(__file__).parent.parent.parent / "super_hefer_cookies.json"


class CaptchaRequiredError(Exception):
    """Raised when user needs to solve CAPTCHA."""
    pass


class SuperHeferScraper(BaseScraper):
    """Scraper for Super Hefer Large (via shopo.co.il platform)."""

    BASE_URL = "https://superhefer.shopo.co.il"
    SEARCH_URL = "https://superhefer.shopo.co.il/search/{query}"

    def get_store_id(self) -> str:
        return "super_hefer"

    def get_store_name(self) -> str:
        return "Super Hefer Large"

    async def _load_cookies(self, context) -> bool:
        """Load saved cookies if they exist."""
        if COOKIES_FILE.exists():
            try:
                cookies = json.loads(COOKIES_FILE.read_text())
                await context.add_cookies(cookies)
                logger.info("Loaded saved Super Hefer cookies")
                return True
            except Exception as e:
                logger.warning(f"Failed to load cookies: {e}")
        return False

    async def _save_cookies(self, context):
        """Save cookies after successful access."""
        try:
            cookies = await context.cookies()
            COOKIES_FILE.write_text(json.dumps(cookies, indent=2))
            logger.info("Saved Super Hefer cookies")
        except Exception as e:
            logger.warning(f"Failed to save cookies: {e}")

    async def _is_captcha_page(self, page: Page) -> bool:
        """Check if current page is a Cloudflare challenge."""
        content = await page.content()
        return "challenge-platform" in content or "cf-turnstile" in content or "רק רגע" in content

    async def _dismiss_popups(self, page: Page):
        """Dismiss any notification popups that may appear."""
        try:
            # Common popup dismiss buttons - including "continue shopping" type buttons
            dismiss_selectors = [
                "button:has-text('המשיכו בקנייה')",
                "button:has-text('המשך לקנייה')",
                "button:has-text('לא תודה')",
                "button:has-text('סגור')",
                "button:has-text('אולי אח\"כ')",
                "button:has-text('לא עכשיו')",
                ".close-btn",
                ".dismiss-btn",
                ".modal-close",
                "button[aria-label='close']",
            ]
            for selector in dismiss_selectors:
                try:
                    btn = await page.query_selector(selector)
                    if btn and await btn.is_visible():
                        await btn.click()
                        await page.wait_for_timeout(500)
                        logger.debug(f"Dismissed popup with: {selector}")
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Popup dismissal: {e}")

    async def _handle_city_popup(self, page: Page):
        """Handle the city selection popup if it appears."""
        try:
            # Check for the choose-area dialog
            city_input = await page.query_selector("#filter-areas-input, input[name='area'], .choose-area-dialog input")
            if city_input and await city_input.is_visible():
                logger.info("City selection popup detected, filling in המעפיל")
                await city_input.click()
                await city_input.fill("המעפיל")
                await page.wait_for_timeout(1500)

                # Wait for autocomplete dropdown and click first option
                # The autocomplete uses sp-auto-complete directive
                autocomplete_option = await page.query_selector(".auto-complete .option, .sp-auto-complete .option, ul[role='listbox'] li")
                if autocomplete_option and await autocomplete_option.is_visible():
                    await autocomplete_option.click()
                    await page.wait_for_timeout(500)
                else:
                    # Fallback: use keyboard to select first suggestion
                    await city_input.press("ArrowDown")
                    await page.wait_for_timeout(300)
                    await city_input.press("Enter")
                    await page.wait_for_timeout(500)

                # Click the "בדיקה" (Check) button
                check_btn = await page.query_selector("button.button-choose.check, button:has-text('בדיקה')")
                if check_btn and await check_btn.is_visible():
                    await check_btn.click()
                    await page.wait_for_timeout(2000)
                    logger.info("City selected successfully")
        except Exception as e:
            logger.debug(f"City popup handling: {e}")

    async def search(self, query: str) -> list[ProductCandidate]:
        """Search for products on Super Hefer."""
        products = []
        page = None

        try:
            page = await self._create_page()

            # Load saved cookies
            context = page.context
            await self._load_cookies(context)

            # Navigate directly to search
            search_url = self.SEARCH_URL.format(query=quote(query))
            logger.info(f"Searching Super Hefer for: {query}")

            await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)  # Wait for JS

            # Check for CAPTCHA
            if await self._is_captcha_page(page):
                logger.warning("CAPTCHA detected - session may need refresh")
                raise CaptchaRequiredError("CAPTCHA required - run 'python -m app.scrapers.super_hefer_auth'")

            # Handle city popup if present
            await self._handle_city_popup(page)

            # Dismiss any notification popups
            await self._dismiss_popups(page)

            # Wait for products to load
            try:
                await page.wait_for_selector("[class*='product'], [class*='Product'], .item", timeout=10000)
            except PlaywrightTimeout:
                logger.warning(f"No products found for query: {query}")
                return []

            # Save cookies on successful access
            await self._save_cookies(context)

            # Extract products
            products = await self._extract_products(page)
            logger.info(f"Found {len(products)} products for: {query}")

        except CaptchaRequiredError:
            raise
        except Exception as e:
            logger.error(f"Super Hefer search failed for '{query}': {e}")
        finally:
            if page:
                await page.close()
            await self._delay()

        return products

    async def _extract_products(self, page: Page) -> list[ProductCandidate]:
        """Extract products from the page."""
        products = []

        # Try various selectors for shopo platform
        selectors_to_try = [
            "[class*='ProductCard']",
            "[class*='productCard']",
            "[class*='product-card']",
            ".product-item",
            "[class*='Product_product']",
            "[class*='item-card']",
        ]

        product_elements = []
        for selector in selectors_to_try:
            elements = await page.query_selector_all(selector)
            if elements:
                product_elements = elements
                logger.debug(f"Found {len(elements)} products with selector: {selector}")
                break

        if not product_elements:
            # Fallback: look for any elements containing price info
            all_elements = await page.query_selector_all("[class*='price']")
            logger.debug(f"Fallback: found {len(all_elements)} price elements")

        seen_names = set()
        for i, element in enumerate(product_elements):
            if len(products) >= settings.scraper_max_results:
                break
            try:
                product = await self._extract_single_product(element, i)
                if product and product.name not in seen_names:
                    products.append(product)
                    seen_names.add(product.name)
            except Exception as e:
                logger.debug(f"Failed to extract product {i}: {e}")
                continue

        return products

    async def _extract_single_product(self, element, index: int) -> ProductCandidate | None:
        """Extract data from a single product element."""
        try:
            # Get all text content to find name and price
            text_content = await element.inner_text()
            lines = [l.strip() for l in text_content.split('\n') if l.strip()]

            if len(lines) < 2:
                return None

            # Usually name is first meaningful line, price contains numbers
            name = None
            price = None

            for line in lines:
                # Skip very short lines
                if len(line) < 2:
                    continue

                # Check if this line looks like a price
                price_match = re.search(r'(\d+\.?\d*)\s*₪?', line)
                if price_match and not name:
                    # Price found before name - skip
                    continue
                elif price_match and name:
                    # Found price after name
                    try:
                        price = float(price_match.group(1))
                        break
                    except ValueError:
                        continue
                elif not name and len(line) > 2:
                    # This looks like a product name
                    name = line

            if not name or not price:
                return None

            # Get URL
            url = None
            link_elem = await element.query_selector("a[href]")
            if link_elem:
                href = await link_elem.get_attribute("href")
                if href:
                    url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

            # Get image
            image_url = None
            img_elem = await element.query_selector("img")
            if img_elem:
                image_url = await img_elem.get_attribute("src") or await img_elem.get_attribute("data-src")
                if image_url and not image_url.startswith("http"):
                    image_url = f"{self.BASE_URL}{image_url}"

            external_id = f"sh_{index}_{hash(name) % 100000}"

            return self._make_product_candidate(
                external_id=external_id,
                name=name,
                price=price,
                url=url,
                image_url=image_url,
                size_descriptor=None,
            )

        except Exception as e:
            logger.debug(f"Error extracting product: {e}")
            return None
