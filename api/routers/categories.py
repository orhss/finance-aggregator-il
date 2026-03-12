"""Category mapping endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import CurrentUser, get_category_service
from api.schemas.categories import (
    AnalysisResponse,
    ApplyMappingsResult,
    BulkAssignRequest,
    BulkAssignResult,
    MappingCreate,
    MappingResponse,
    MerchantMappingCreate,
    MerchantMappingResponse,
    UnmappedCategory,
)
from api.schemas.common import MessageResponse
from services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])


# ==================== Provider Mappings ====================

@router.get("/mappings", response_model=List[MappingResponse])
def list_mappings(
    provider: Optional[str] = None,
    _: str = CurrentUser,
    svc: CategoryService = Depends(get_category_service),
):
    return [MappingResponse.model_validate(m) for m in svc.get_all_mappings(provider)]


@router.post("/mappings", response_model=MappingResponse)
def create_mapping(
    body: MappingCreate,
    _: str = CurrentUser,
    svc: CategoryService = Depends(get_category_service),
):
    mapping = svc.add_mapping(body.provider, body.raw_category, body.unified_category)
    return MappingResponse.model_validate(mapping)


@router.delete("/mappings", response_model=MessageResponse)
def delete_mapping(
    provider: str,
    raw_category: str,
    _: str = CurrentUser,
    svc: CategoryService = Depends(get_category_service),
):
    deleted = svc.remove_mapping(provider, raw_category)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    return MessageResponse(message="Mapping deleted")


@router.post("/mappings/apply", response_model=ApplyMappingsResult)
def apply_mappings(
    provider: Optional[str] = None,
    _: str = CurrentUser,
    svc: CategoryService = Depends(get_category_service),
):
    updated = svc.apply_mappings_to_transactions(provider=provider)
    return ApplyMappingsResult(updated=updated, total=sum(updated.values()))


# ==================== Unmapped ====================

@router.get("/unmapped", response_model=List[UnmappedCategory])
def unmapped_categories(
    provider: Optional[str] = None,
    _: str = CurrentUser,
    svc: CategoryService = Depends(get_category_service),
):
    raw = svc.get_unmapped_categories(provider=provider)
    return [UnmappedCategory(**u) for u in raw]


# ==================== Analysis ====================

@router.get("/analysis", response_model=AnalysisResponse)
def category_analysis(
    _: str = CurrentUser,
    svc: CategoryService = Depends(get_category_service),
):
    raw = svc.analyze_categories()
    return AnalysisResponse(**raw)


@router.get("/unified", response_model=List[str])
def unified_categories(
    _: str = CurrentUser,
    svc: CategoryService = Depends(get_category_service),
):
    return svc.get_unified_categories()


# ==================== Merchant Mappings ====================

@router.get("/merchants", response_model=List[MerchantMappingResponse])
def list_merchant_mappings(
    provider: Optional[str] = None,
    _: str = CurrentUser,
    svc: CategoryService = Depends(get_category_service),
):
    return [MerchantMappingResponse.model_validate(m) for m in svc.get_all_merchant_mappings(provider)]


@router.post("/merchants", response_model=MerchantMappingResponse)
def create_merchant_mapping(
    body: MerchantMappingCreate,
    _: str = CurrentUser,
    svc: CategoryService = Depends(get_category_service),
):
    mapping = svc.add_merchant_mapping(body.pattern, body.category, body.provider, body.match_type)
    return MerchantMappingResponse.model_validate(mapping)


@router.delete("/merchants", response_model=MessageResponse)
def delete_merchant_mapping(
    pattern: str,
    provider: Optional[str] = None,
    _: str = CurrentUser,
    svc: CategoryService = Depends(get_category_service),
):
    deleted = svc.remove_merchant_mapping(pattern, provider)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant mapping not found")
    return MessageResponse(message="Merchant mapping deleted")


@router.get("/merchants/suggest", response_model=list)
def suggest_merchants(
    min_transactions: int = 2,
    provider: Optional[str] = None,
    _: str = CurrentUser,
    svc: CategoryService = Depends(get_category_service),
):
    return svc.get_uncategorized_by_merchant(min_transactions=min_transactions, provider=provider)


# ==================== Bulk Assign ====================

@router.post("/bulk-assign", response_model=BulkAssignResult)
def bulk_assign(
    body: BulkAssignRequest,
    _: str = CurrentUser,
    svc: CategoryService = Depends(get_category_service),
):
    if body.save_mapping and body.merchant_pattern:
        result = svc.bulk_set_category_with_mapping(
            merchant_pattern=body.merchant_pattern,
            category=body.category,
            transaction_ids=body.transaction_ids,
            provider=body.provider,
        )
        return BulkAssignResult(**result)
    else:
        count = svc.bulk_set_category(body.transaction_ids, body.category)
        return BulkAssignResult(transactions_updated=count, mapping_created=False)
