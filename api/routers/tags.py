"""Tag endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import CurrentUser, get_tag_service
from api.schemas.common import CountResponse, MessageResponse
from api.schemas.tags import (
    BulkTagRequest,
    RenameTagRequest,
    TagResponse,
    TagStatsResponse,
    TagTransactionRequest,
)
from services.tag_service import TagService

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=List[TagResponse])
def list_tags(
    _: str = CurrentUser,
    svc: TagService = Depends(get_tag_service),
):
    return [TagResponse.model_validate(t) for t in svc.get_all_tags()]


@router.get("/stats", response_model=List[TagStatsResponse])
def tag_stats(
    _: str = CurrentUser,
    svc: TagService = Depends(get_tag_service),
):
    return [TagStatsResponse(**s) for s in svc.get_tag_stats()]


@router.get("/untagged-count", response_model=CountResponse)
def untagged_count(
    _: str = CurrentUser,
    svc: TagService = Depends(get_tag_service),
):
    return CountResponse(count=svc.get_untagged_count())


@router.post("/{transaction_id}/tag", response_model=CountResponse)
def tag_transaction(
    transaction_id: int,
    body: TagTransactionRequest,
    _: str = CurrentUser,
    svc: TagService = Depends(get_tag_service),
):
    try:
        added = svc.tag_transaction(transaction_id, body.tags)
        return CountResponse(count=added)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{transaction_id}/untag", response_model=CountResponse)
def untag_transaction(
    transaction_id: int,
    body: TagTransactionRequest,
    _: str = CurrentUser,
    svc: TagService = Depends(get_tag_service),
):
    removed = svc.untag_transaction(transaction_id, body.tags)
    return CountResponse(count=removed)


@router.post("/bulk", response_model=CountResponse)
def bulk_tag(
    body: BulkTagRequest,
    _: str = CurrentUser,
    svc: TagService = Depends(get_tag_service),
):
    if body.merchant_pattern:
        count = svc.bulk_tag_by_merchant(body.merchant_pattern, body.tag_names)
    elif body.category:
        count = svc.bulk_tag_by_category(body.category, body.tag_names)
    else:
        raise HTTPException(status_code=400, detail="Provide merchant_pattern or category")
    return CountResponse(count=count)


@router.patch("/{name}/rename", response_model=MessageResponse)
def rename_tag(
    name: str,
    body: RenameTagRequest,
    _: str = CurrentUser,
    svc: TagService = Depends(get_tag_service),
):
    success = svc.rename_tag(name, body.new_name)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tag '{name}' not found")
    return MessageResponse(message=f"Renamed '{name}' to '{body.new_name}'")


@router.delete("/{name}", response_model=MessageResponse)
def delete_tag(
    name: str,
    _: str = CurrentUser,
    svc: TagService = Depends(get_tag_service),
):
    success = svc.delete_tag(name)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tag '{name}' not found")
    return MessageResponse(message=f"Deleted tag '{name}'")
