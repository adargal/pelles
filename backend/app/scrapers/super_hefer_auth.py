#!/usr/bin/env python
"""
Super Hefer Authentication Script

This script opens a visible browser window for the user to solve the
Cloudflare CAPTCHA. Once solved, it saves the session cookies for
subsequent automated requests.

Run this when you see "CAPTCHA required" errors.
"""

import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright

COOKIES_FILE = Path(__file__).parent.parent.parent / "super_hefer_cookies.json"
TARGET_URL = "https://superhefer.shopo.co.il"
SEARCH_URL = "https://superhefer.shopo.co.il/search?q=חלב"


async def authenticate():
    print("=" * 60)
    print("Super Hefer Authentication")
    print("=" * 60)
    print()
    print("A browser window will open. Please:")
    print("1. Complete the Cloudflare CAPTCHA if prompted")
    print("2. Select your city/branch when asked")
    print("3. If a button doesn't work, try right-clicking and 'Open in new tab'")
    print("4. Navigate until you see PRODUCTS on the page")
    print("5. Press ENTER here when you see products")
    print()
    print("Opening browser...")
    print()

    async with async_playwright() as p:
        # Launch visible browser with more realistic settings
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
            ]
        )

        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="he-IL",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        # Remove webdriver flag
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        page = await context.new_page()

        try:
            # Go to the site
            await page.goto(TARGET_URL, wait_until="domcontentloaded")

            print("Complete the setup in the browser window.")
            print()
            print("TIPS:")
            print("- If 'Approve' button doesn't work, try clicking elsewhere first")
            print("- Try refreshing the page (F5) after selecting city")
            print("- Or navigate manually to: " + SEARCH_URL)
            print()
            print("Press ENTER here when you can see products...")
            print()

            # Wait for user to press Enter
            await asyncio.get_event_loop().run_in_executor(None, input)

            # Save cookies
            cookies = await context.cookies()
            COOKIES_FILE.write_text(json.dumps(cookies, indent=2))

            print()
            print("=" * 60)
            print("SUCCESS! Cookies saved to:", COOKIES_FILE)
            print("=" * 60)
            print()
            print("You can now use the Super Hefer scraper.")
            print("The cookies should remain valid for a while.")
            print()

            # Give user a moment to see the success
            await asyncio.sleep(2)

            return True

        except Exception as e:
            print(f"Error: {e}")
            return False

        finally:
            await browser.close()


async def verify_cookies():
    """Test if saved cookies work."""
    if not COOKIES_FILE.exists():
        print("No saved cookies found. Run authentication first.")
        return False

    print("Testing saved cookies...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        # Load cookies
        cookies = json.loads(COOKIES_FILE.read_text())
        await context.add_cookies(cookies)

        page = await context.new_page()

        try:
            await page.goto(
                "https://superhefer.shopo.co.il/search?q=חלב",
                wait_until="domcontentloaded",
                timeout=30000
            )
            await page.wait_for_timeout(3000)

            content = await page.content()
            is_challenge = (
                "challenge-platform" in content or
                "cf-turnstile" in content or
                "רק רגע" in content
            )

            if is_challenge:
                print("Cookies expired or invalid. Run authentication again.")
                return False

            print("Cookies are valid!")
            return True

        except Exception as e:
            print(f"Error testing cookies: {e}")
            return False

        finally:
            await browser.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        asyncio.run(verify_cookies())
    else:
        asyncio.run(authenticate())
