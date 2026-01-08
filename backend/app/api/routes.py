from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete

from app.database import get_db
from app.models import SearchCache
from app.schemas import ComparisonRequest, ComparisonResponse, OverrideRequest
from app.services.comparison import ComparisonService

router = APIRouter()


@router.post("/compare", response_model=ComparisonResponse)
async def compare_prices(
    request: ComparisonRequest,
    db: AsyncSession = Depends(get_db),
):
    if not request.items:
        raise HTTPException(status_code=400, detail="No items provided")

    # Filter empty lines and strip whitespace
    items = [item.strip() for item in request.items if item.strip()]
    if not items:
        raise HTTPException(status_code=400, detail="No valid items provided")

    service = ComparisonService(db)
    result = await service.compare(items)
    return result


@router.post("/compare/{comparison_id}/override", response_model=ComparisonResponse)
async def override_match(
    comparison_id: str,
    request: OverrideRequest,
    db: AsyncSession = Depends(get_db),
):
    service = ComparisonService(db)
    result = await service.override_selection(
        comparison_id=comparison_id,
        item_query=request.item_query,
        store_id=request.store_id,
        product_id=request.product_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Comparison not found")
    return result


@router.get("/stores")
async def list_stores():
    """List available stores for comparison."""
    return {
        "stores": [
            {"id": "shufersal", "name": "Shufersal", "enabled": True},
            {"id": "super_hefer", "name": "Super Hefer Large", "enabled": True},
        ]
    }


@router.delete("/cache")
async def clear_cache(db: AsyncSession = Depends(get_db)):
    """Clear all cached search results."""
    result = await db.execute(delete(SearchCache))
    await db.commit()
    return {"message": "Cache cleared", "deleted_count": result.rowcount}


@router.delete("/cache/{store_id}")
async def clear_store_cache(store_id: str, db: AsyncSession = Depends(get_db)):
    """Clear cached search results for a specific store."""
    result = await db.execute(
        delete(SearchCache).where(SearchCache.store_id == store_id)
    )
    await db.commit()
    return {"message": f"Cache cleared for {store_id}", "deleted_count": result.rowcount}
