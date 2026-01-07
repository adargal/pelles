from abc import ABC, abstractmethod
from datetime import datetime
import asyncio
import logging

from playwright.async_api import async_playwright, Browser, Page

from app.schemas import ProductCandidate
from app.config import settings

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for store scrapers."""

    _browser: Browser | None = None
    _playwright = None

    @classmethod
    async def get_browser(cls) -> Browser:
        """Get or create a shared browser instance."""
        if cls._browser is None:
            cls._playwright = await async_playwright().start()
            cls._browser = await cls._playwright.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
        return cls._browser

    @classmethod
    async def close_browser(cls):
        """Close the shared browser instance."""
        if cls._browser:
            await cls._browser.close()
            cls._browser = None
        if cls._playwright:
            await cls._playwright.stop()
            cls._playwright = None

    @abstractmethod
    def get_store_id(self) -> str:
        """Return the unique store identifier."""
        pass

    @abstractmethod
    def get_store_name(self) -> str:
        """Return the display name for the store."""
        pass

    @abstractmethod
    async def search(self, query: str) -> list[ProductCandidate]:
        """
        Search for products matching the query.

        Args:
            query: The search term (may be in Hebrew)

        Returns:
            List of ProductCandidate objects (up to max_results)
        """
        pass

    async def _create_page(self) -> Page:
        """Create a new page with common settings."""
        browser = await self.get_browser()
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="he-IL",
        )
        # Remove webdriver flag to avoid detection
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        page = await context.new_page()
        page.set_default_timeout(settings.scraper_timeout_seconds * 1000)
        return page

    async def _delay(self):
        """Add delay between requests to respect rate limits."""
        await asyncio.sleep(settings.scraper_delay_seconds)

    def _make_product_candidate(
        self,
        external_id: str,
        name: str,
        price: float,
        url: str | None = None,
        image_url: str | None = None,
        size_descriptor: str | None = None,
    ) -> ProductCandidate:
        """Helper to create a ProductCandidate with store info."""
        return ProductCandidate(
            id=f"{self.get_store_id()}_{external_id}",
            store_id=self.get_store_id(),
            name=name,
            price=price,
            url=url,
            image_url=image_url,
            size_descriptor=size_descriptor,
            fetched_at=datetime.utcnow(),
        )
