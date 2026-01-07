import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SearchCache
from app.schemas import ProductCandidate
from app.scrapers import BaseScraper, ShufersalScraper, SuperHeferScraper
from app.config import settings

logger = logging.getLogger(__name__)


class SearchService:
    """Service for searching products across stores with caching."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.scrapers: dict[str, BaseScraper] = {
            "shufersal": ShufersalScraper(),
            "super_hefer": SuperHeferScraper(),
        }

    def get_all_store_ids(self) -> list[str]:
        """Get list of all available store IDs."""
        return list(self.scrapers.keys())

    def get_store_name(self, store_id: str) -> str:
        """Get display name for a store."""
        scraper = self.scrapers.get(store_id)
        return scraper.get_store_name() if scraper else store_id

    async def search(
        self,
        query: str,
        store_id: str,
        use_cache: bool = True,
    ) -> list[ProductCandidate]:
        """
        Search for products in a specific store.
        Uses cache if available and not expired.
        """
        normalized_query = query.strip().lower()

        # Try cache first
        if use_cache:
            cached = await self._get_cached_results(store_id, normalized_query)
            if cached is not None:
                logger.debug(f"Cache hit for {store_id}:{normalized_query}")
                return cached

        # Fetch from scraper
        scraper = self.scrapers.get(store_id)
        if not scraper:
            logger.error(f"Unknown store: {store_id}")
            return []

        try:
            results = await scraper.search(query)

            # Cache results
            await self._cache_results(store_id, normalized_query, results)

            return results

        except Exception as e:
            logger.error(f"Search failed for {store_id}:{query}: {e}")
            return []

    async def search_all_stores(
        self,
        query: str,
        use_cache: bool = True,
    ) -> dict[str, list[ProductCandidate]]:
        """
        Search for products across all stores.
        Returns dict mapping store_id to list of products.
        """
        results = {}
        for store_id in self.scrapers:
            results[store_id] = await self.search(query, store_id, use_cache)
        return results

    async def _get_cached_results(
        self,
        store_id: str,
        normalized_query: str,
    ) -> list[ProductCandidate] | None:
        """Get cached search results if they exist and aren't expired."""
        cache_cutoff = datetime.utcnow() - timedelta(days=settings.cache_ttl_days)

        result = await self.db.execute(
            select(SearchCache).where(
                SearchCache.store_id == store_id,
                SearchCache.query_normalized == normalized_query,
                SearchCache.fetched_at >= cache_cutoff,
            )
        )
        cache_entry = result.scalar_one_or_none()

        if cache_entry:
            try:
                data = json.loads(cache_entry.results_json)
                return [ProductCandidate(**item) for item in data]
            except Exception as e:
                logger.warning(f"Failed to parse cached results: {e}")
                return None

        return None

    async def _cache_results(
        self,
        store_id: str,
        normalized_query: str,
        results: list[ProductCandidate],
    ):
        """Cache search results."""
        try:
            results_json = json.dumps(
                [product.model_dump(mode="json") for product in results]
            )

            # Upsert cache entry
            existing = await self.db.execute(
                select(SearchCache).where(
                    SearchCache.store_id == store_id,
                    SearchCache.query_normalized == normalized_query,
                )
            )
            cache_entry = existing.scalar_one_or_none()

            if cache_entry:
                cache_entry.results_json = results_json
                cache_entry.fetched_at = datetime.utcnow()
            else:
                cache_entry = SearchCache(
                    store_id=store_id,
                    query_normalized=normalized_query,
                    results_json=results_json,
                    fetched_at=datetime.utcnow(),
                )
                self.db.add(cache_entry)

            await self.db.commit()

        except Exception as e:
            logger.error(f"Failed to cache results: {e}")
            await self.db.rollback()
