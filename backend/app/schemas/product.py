from datetime import datetime
from enum import Enum
from pydantic import BaseModel


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ProductCandidate(BaseModel):
    id: str
    store_id: str
    name: str
    price: float
    url: str | None = None
    image_url: str | None = None
    size_descriptor: str | None = None
    fetched_at: datetime


class StoreMatch(BaseModel):
    product: ProductCandidate | None = None
    confidence: ConfidenceLevel | None = None
    alternatives: list[ProductCandidate] = []
    warning: str | None = None
    match_score: float = 0.0


class ItemMatch(BaseModel):
    query: str
    matches: dict[str, StoreMatch]  # store_id -> StoreMatch


class StoreSummary(BaseModel):
    store_id: str
    store_name: str
    total_price: float
    matched_count: int
    missing_count: int
    warned_count: int
    is_recommended: bool = False
    as_of: datetime | None = None


class ComparisonRequest(BaseModel):
    items: list[str]


class ComparisonResponse(BaseModel):
    comparison_id: str
    stores: list[StoreSummary]
    items: list[ItemMatch]


class OverrideRequest(BaseModel):
    item_query: str
    store_id: str
    product_id: str
