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
                "button.close-dialog-corner-button",
                "button:has-text('המשיכו בקנייה')",
                "button:has-text('המשך לקנייה')",
                "button:has-text('אישור')",
                "button:has-text('לא תודה')",
                "button:has-text('סגור')",
                "button:has-text('אולי אח\"כ')",
                "button:has-text('לא עכשיו')",
                ".close-btn",
                ".dismiss-btn",
                ".modal-close",
                "button[aria-label='close']",
                "button[aria-label='סגור']",
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

        # The shopo platform uses sp-product custom elements
        product_elements = await page.query_selector_all("sp-product[aria-labelledby]")
        logger.debug(f"Found {len(product_elements)} sp-product elements")

        if not product_elements:
            # Fallback to product-item divs
            product_elements = await page.query_selector_all(".product-item")
            logger.debug(f"Fallback: found {len(product_elements)} product-item elements")

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
            # Get product ID from aria-labelledby attribute (e.g., "product_2909971_name")
            aria_labelledby = await element.get_attribute("aria-labelledby")
            external_id = None
            if aria_labelledby:
                # Extract ID like "2909971" from "product_2909971_name"
                id_match = re.search(r'product_(\d+)_name', aria_labelledby)
                if id_match:
                    external_id = id_match.group(1)

            # Get product name from the .name element with aria-label
            name = None
            name_elem = await element.query_selector(".name[aria-label]")
            if name_elem:
                name = await name_elem.get_attribute("aria-label")
            if not name:
                # Fallback to inner text of .name element
                name_elem = await element.query_selector(".name")
                if name_elem:
                    name = (await name_elem.inner_text()).strip()

            if not name:
                return None

            # Get price from meta[itemprop="price"] or span.price
            price = None
            price_meta = await element.query_selector("meta[itemprop='price']")
            if price_meta:
                price_content = await price_meta.get_attribute("content")
                if price_content:
                    try:
                        price = float(price_content)
                    except ValueError:
                        pass

            if price is None:
                # Fallback to span.price text
                price_elem = await element.query_selector(".sp-product-price .price")
                if price_elem:
                    price_text = await price_elem.inner_text()
                    # Extract number from text like "₪9.90"
                    price_match = re.search(r'(\d+\.?\d*)', price_text)
                    if price_match:
                        try:
                            price = float(price_match.group(1))
                        except ValueError:
                            pass

            if price is None:
                return None

            # Get size/weight descriptor
            size_descriptor = None
            weight_elem = await element.query_selector(".weight")
            if weight_elem:
                weight_text = (await weight_elem.inner_text()).strip()
                # Remove leading "| " if present
                size_descriptor = weight_text.lstrip("| ").strip()

            # Get product image URL from background-image style
            image_url = None
            img_div = await element.query_selector(".image[style*='background-image']")
            if img_div:
                style = await img_div.get_attribute("style")
                if style:
                    # Extract URL from background-image: url("...")
                    url_match = re.search(r'url\(["\']?([^"\')\s]+)["\']?\)', style)
                    if url_match:
                        image_url = url_match.group(1)

            # Generate external ID if not found
            if not external_id:
                external_id = f"sh_{index}_{hash(name) % 100000}"

            return self._make_product_candidate(
                external_id=external_id,
                name=name,
                price=price,
                url=None,  # No direct product URL in the search results
                image_url=image_url,
                size_descriptor=size_descriptor,
            )

        except Exception as e:
            logger.debug(f"Error extracting product: {e}")
            return None
