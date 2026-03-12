"""Category schemas."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class MappingResponse(BaseModel):
    id: int
    provider: str
    raw_category: str
    unified_category: str

    class Config:
        from_attributes = True


class MappingCreate(BaseModel):
    provider: str
    raw_category: str
    unified_category: str


class MerchantMappingResponse(BaseModel):
    id: int
    pattern: str
    category: str
    provider: Optional[str] = None
    match_type: str

    class Config:
        from_attributes = True


class MerchantMappingCreate(BaseModel):
    pattern: str
    category: str
    provider: Optional[str] = None
    match_type: str = "startswith"


class UnmappedCategory(BaseModel):
    provider: str
    raw_category: str
    count: int
    sample_merchants: List[str] = []


class AnalysisResponse(BaseModel):
    providers: List[Dict[str, Any]]
    totals: Dict[str, Any]


class BulkAssignRequest(BaseModel):
    transaction_ids: List[int]
    category: str
    merchant_pattern: Optional[str] = None
    provider: Optional[str] = None
    save_mapping: bool = True


class ApplyMappingsResult(BaseModel):
    updated: Dict[str, int]
    total: int


class BulkAssignResult(BaseModel):
    transactions_updated: int
    mapping_created: bool
