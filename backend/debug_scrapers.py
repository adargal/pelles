#!/usr/bin/env python
"""Debug script to test scrapers directly."""

import asyncio
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from app.scrapers import ShufersalScraper, SuperHeferScraper


async def test_shufersal():
    print("\n" + "=" * 50)
    print("Testing Shufersal Scraper")
    print("=" * 50)

    scraper = ShufersalScraper()
    query = "חלב"

    print(f"\nSearching for: {query}")

    try:
        results = await scraper.search(query)
        print(f"\nFound {len(results)} products:")

        for i, product in enumerate(results[:5], 1):
            print(f"\n{i}. {product.name}")
            print(f"   Price: {product.price} ₪")
            print(f"   URL: {product.url}")
            print(f"   Image: {product.image_url}")
            print(f"   Size: {product.size_descriptor}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


async def test_super_hefer():
    print("\n" + "=" * 50)
    print("Testing Super Hefer Scraper")
    print("=" * 50)

    scraper = SuperHeferScraper()
    query = "חלב"

    print(f"\nSearching for: {query}")

    try:
        results = await scraper.search(query)
        print(f"\nFound {len(results)} products:")

        for i, product in enumerate(results[:5], 1):
            print(f"\n{i}. {product.name}")
            print(f"   Price: {product.price} ₪")
            print(f"   URL: {product.url}")
            print(f"   Image: {product.image_url}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


async def debug_shufersal_page():
    """Debug by saving page HTML and screenshot."""
    print("\n" + "=" * 50)
    print("Debugging Shufersal Page Structure")
    print("=" * 50)

    from playwright.async_api import async_playwright
    from urllib.parse import quote

    query = "חלב"
    url = f"https://www.shufersal.co.il/online/he/search?text={quote(query)}"

    print(f"\nFetching: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Use domcontentloaded instead of networkidle, then wait for products
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            print("Page loaded, waiting for content...")

            # Wait a bit for JS to render
            await page.wait_for_timeout(5000)

            # Save screenshot
            await page.screenshot(path="debug_shufersal.png", full_page=True)
            print("Saved screenshot to debug_shufersal.png")

            # Save HTML
            html = await page.content()
            with open("debug_shufersal.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("Saved HTML to debug_shufersal.html")

            # Try various selectors
            selectors_to_try = [
                "[data-product-code]",
                ".product-tile",
                ".productTile",
                "[class*='product']",
                "[class*='Product']",
                ".tile",
                "ul.products li",
                ".search-results li",
                "[data-product]",
            ]

            print("\nTrying selectors:")
            for selector in selectors_to_try:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"  ✓ '{selector}' - found {len(elements)} elements")

                    # Get some info about the first element
                    if elements:
                        first = elements[0]
                        inner = await first.inner_text()
                        print(f"    First element text preview: {inner[:100]}...")
                else:
                    print(f"  ✗ '{selector}' - not found")

            # Look for any price elements
            print("\nLooking for price elements:")
            price_selectors = [
                "[class*='price']",
                "[class*='Price']",
                ".price",
                "[data-price]",
            ]
            for selector in price_selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"  ✓ '{selector}' - found {len(elements)} elements")

        finally:
            await browser.close()


async def debug_super_hefer_page():
    """Debug Super Hefer page structure."""
    print("\n" + "=" * 50)
    print("Debugging Super Hefer Page Structure")
    print("=" * 50)

    from playwright.async_api import async_playwright
    from urllib.parse import quote
    from pathlib import Path
    import json

    query = "חלב"
    url = f"https://superhefer.shopo.co.il/search/{quote(query)}"
    cookies_file = Path(__file__).parent / "super_hefer_cookies.json"

    print(f"\nFetching: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="he-IL",
        )

        # Remove webdriver flag
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # Load saved cookies
        if cookies_file.exists():
            print("Loading saved cookies...")
            cookies = json.loads(cookies_file.read_text())
            await context.add_cookies(cookies)
        else:
            print("WARNING: No cookies found! Run 'python -m app.scrapers.super_hefer_auth' first")

        page = await context.new_page()

        try:
            # Navigate directly to search
            print(f"Navigating to search: {url}")
            response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            print("Page loaded, waiting for content...")
            await page.wait_for_timeout(3000)
            print(f"Response status: {response.status if response else 'No response'}")

            # Handle city popup if it appears
            city_input = await page.query_selector("#filter-areas-input, input[name='area'], .choose-area-dialog input")
            if city_input and await city_input.is_visible():
                print("City popup detected, filling in המעפיל...")
                await city_input.click()
                await city_input.fill("המעפיל")
                await page.wait_for_timeout(1500)

                autocomplete_option = await page.query_selector(".auto-complete .option, .sp-auto-complete .option, ul[role='listbox'] li")
                if autocomplete_option and await autocomplete_option.is_visible():
                    print("Clicking autocomplete option...")
                    await autocomplete_option.click()
                    await page.wait_for_timeout(500)
                else:
                    print("Using keyboard to select suggestion...")
                    await city_input.press("ArrowDown")
                    await page.wait_for_timeout(300)
                    await city_input.press("Enter")
                    await page.wait_for_timeout(500)

                check_btn = await page.query_selector("button.button-choose.check, button:has-text('בדיקה')")
                if check_btn and await check_btn.is_visible():
                    await check_btn.click()
                    await page.wait_for_timeout(2000)
                    print("City selected!")

            # Dismiss any popups that appear
            for dismiss_selector in ["button:has-text('המשיכו בקנייה')", "button:has-text('המשך לקנייה')", "button:has-text('סגור')"]:
                try:
                    btn = await page.query_selector(dismiss_selector)
                    if btn and await btn.is_visible():
                        print(f"Dismissing popup with: {dismiss_selector}")
                        await btn.click()
                        await page.wait_for_timeout(1000)
                except Exception:
                    pass

            # Save screenshot
            await page.screenshot(path="debug_super_hefer.png", full_page=True)
            print("Saved screenshot to debug_super_hefer.png")

            # Save HTML
            html = await page.content()
            with open("debug_super_hefer.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("Saved HTML to debug_super_hefer.html")

            # Check current URL (might have redirected)
            print(f"Current URL: {page.url}")

            # Try various selectors
            selectors_to_try = [
                ".product-card",
                ".product-item",
                "[class*='product']",
                "[class*='Product']",
                ".item-card",
                ".item",
                "[class*='item']",
                "[class*='card']",
            ]

            print("\nTrying selectors:")
            for selector in selectors_to_try:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"  ✓ '{selector}' - found {len(elements)} elements")
                else:
                    print(f"  ✗ '{selector}' - not found")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            await browser.close()


async def main():
    print("Scraper Debug Tool")
    print("==================")
    print("\n1. Test Shufersal scraper")
    print("2. Test Super Hefer scraper")
    print("3. Debug Shufersal page (save HTML/screenshot)")
    print("4. Debug Super Hefer page (save HTML/screenshot)")
    print("5. Run all")

    choice = input("\nChoice [1-5]: ").strip()

    if choice == "1":
        await test_shufersal()
    elif choice == "2":
        await test_super_hefer()
    elif choice == "3":
        await debug_shufersal_page()
    elif choice == "4":
        await debug_super_hefer_page()
    elif choice == "5":
        await debug_shufersal_page()
        await debug_super_hefer_page()
        await test_shufersal()
        await test_super_hefer()
    else:
        print("Invalid choice")

    # Clean up browser
    from app.scrapers.base import BaseScraper
    await BaseScraper.close_browser()


if __name__ == "__main__":
    asyncio.run(main())
