"""Tag schemas."""

from typing import List, Optional
from pydantic import BaseModel


class TagResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class TagStatsResponse(BaseModel):
    name: str
    count: int
    total_amount: float


class TagTransactionRequest(BaseModel):
    tags: List[str]


class BulkTagRequest(BaseModel):
    merchant_pattern: Optional[str] = None
    category: Optional[str] = None
    tag_names: List[str]


class RenameTagRequest(BaseModel):
    new_name: str
