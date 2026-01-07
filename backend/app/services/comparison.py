import logging
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import (
    ProductCandidate,
    ItemMatch,
    StoreMatch,
    StoreSummary,
    ComparisonResponse,
    ConfidenceLevel,
)
from app.services.search import SearchService
from app.services.matcher import find_best_match
from app.config import settings

logger = logging.getLogger(__name__)


# In-memory store for comparison sessions (for override functionality)
# In production, this could be Redis or database-backed
_comparison_cache: dict[str, ComparisonResponse] = {}


class ComparisonService:
    """Service for comparing prices across stores."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.search_service = SearchService(db)

    async def compare(self, items: list[str]) -> ComparisonResponse:
        """
        Compare prices for a list of items across all stores.
        """
        comparison_id = str(uuid.uuid4())[:8]
        store_ids = self.search_service.get_all_store_ids()

        item_matches: list[ItemMatch] = []

        # Process each item
        for item_query in items:
            logger.info(f"Processing item: {item_query}")

            # Search all stores for this item
            all_results = await self.search_service.search_all_stores(item_query)

            # Find best match for each store
            matches: dict[str, StoreMatch] = {}

            for store_id in store_ids:
                candidates = all_results.get(store_id, [])
                match_result = find_best_match(item_query, candidates)

                if match_result:
                    matches[store_id] = StoreMatch(
                        product=match_result.product,
                        confidence=match_result.confidence,
                        alternatives=[p for p, _ in [(c, 0) for c in candidates if c.id != match_result.product.id][:4]],
                        warning=match_result.warning,
                        match_score=match_result.score,
                    )
                else:
                    matches[store_id] = StoreMatch(
                        product=None,
                        confidence=None,
                        alternatives=candidates[:5],
                        warning="No match found",
                        match_score=0.0,
                    )

            item_matches.append(ItemMatch(query=item_query, matches=matches))

        # Calculate store summaries
        store_summaries = self._calculate_summaries(item_matches, store_ids)

        # Determine recommendation
        self._determine_recommendation(store_summaries, len(items))

        response = ComparisonResponse(
            comparison_id=comparison_id,
            stores=store_summaries,
            items=item_matches,
        )

        # Cache for override functionality
        _comparison_cache[comparison_id] = response

        return response

    def _calculate_summaries(
        self,
        item_matches: list[ItemMatch],
        store_ids: list[str],
    ) -> list[StoreSummary]:
        """Calculate summary statistics for each store."""
        summaries = []

        for store_id in store_ids:
            total_price = 0.0
            matched_count = 0
            missing_count = 0
            warned_count = 0
            oldest_fetch: datetime | None = None

            for item in item_matches:
                store_match = item.matches.get(store_id)
                if store_match and store_match.product:
                    total_price += store_match.product.price
                    matched_count += 1

                    if store_match.warning:
                        warned_count += 1

                    # Track oldest fetch time
                    if oldest_fetch is None or store_match.product.fetched_at < oldest_fetch:
                        oldest_fetch = store_match.product.fetched_at
                else:
                    missing_count += 1

            summaries.append(
                StoreSummary(
                    store_id=store_id,
                    store_name=self.search_service.get_store_name(store_id),
                    total_price=round(total_price, 2),
                    matched_count=matched_count,
                    missing_count=missing_count,
                    warned_count=warned_count,
                    is_recommended=False,
                    as_of=oldest_fetch,
                )
            )

        return summaries

    def _determine_recommendation(
        self,
        summaries: list[StoreSummary],
        total_items: int,
    ):
        """Determine which store to recommend based on coverage and price."""
        min_coverage = settings.min_coverage_for_recommendation

        eligible = []
        for summary in summaries:
            coverage = summary.matched_count / total_items if total_items > 0 else 0
            if coverage >= min_coverage:
                eligible.append(summary)

        if not eligible:
            logger.info("No store meets minimum coverage threshold for recommendation")
            return

        # Find cheapest among eligible
        cheapest = min(eligible, key=lambda s: s.total_price)
        cheapest.is_recommended = True

    async def override_selection(
        self,
        comparison_id: str,
        item_query: str,
        store_id: str,
        product_id: str,
    ) -> ComparisonResponse | None:
        """Override the selected product for an item-store pair."""
        comparison = _comparison_cache.get(comparison_id)
        if not comparison:
            return None

        # Find the item
        for item in comparison.items:
            if item.query == item_query:
                store_match = item.matches.get(store_id)
                if not store_match:
                    continue

                # Find product in alternatives
                new_product = None
                for alt in store_match.alternatives:
                    if alt.id == product_id:
                        new_product = alt
                        break

                if new_product:
                    # Swap current product to alternatives
                    old_product = store_match.product
                    new_alternatives = [p for p in store_match.alternatives if p.id != product_id]
                    if old_product:
                        new_alternatives.insert(0, old_product)

                    # Update match
                    store_match.product = new_product
                    store_match.alternatives = new_alternatives[:4]
                    store_match.confidence = ConfidenceLevel.HIGH  # User override = high confidence
                    store_match.warning = "User selected"
                    store_match.match_score = 1.0

                break

        # Recalculate summaries
        store_ids = self.search_service.get_all_store_ids()
        comparison.stores = self._calculate_summaries(comparison.items, store_ids)
        self._determine_recommendation(comparison.stores, len(comparison.items))

        # Update cache
        _comparison_cache[comparison_id] = comparison

        return comparison
