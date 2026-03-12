"""Sync schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class SyncHistoryResponse(BaseModel):
    id: int
    sync_type: str
    institution: Optional[str] = None
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    records_added: int
    records_updated: int
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class SyncRequest(BaseModel):
    account_index: Optional[int] = None
    months_back: Optional[int] = None


class SyncProgress(BaseModel):
    type: str  # "progress" | "success" | "error" | "ping"
    message: str
    institution: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
