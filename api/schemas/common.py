"""Common response schemas."""

from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    has_next: bool


class ErrorResponse(BaseModel):
    detail: str


class MessageResponse(BaseModel):
    message: str


class CountResponse(BaseModel):
    count: int
