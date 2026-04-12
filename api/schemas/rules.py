"""Rules schemas."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class RuleResponse(BaseModel):
    pattern: str
    match_type: str
    category: Optional[str] = None
    tags: List[str] = []
    remove_tags: List[str] = []
    description: Optional[str] = None
    enabled: bool = True


class RuleCreate(BaseModel):
    pattern: str
    match_type: str = "contains"
    category: Optional[str] = None
    tags: List[str] = []
    remove_tags: List[str] = []
    description: Optional[str] = None


class ApplyRulesRequest(BaseModel):
    transaction_ids: Optional[List[int]] = None
    only_uncategorized: bool = False
    dry_run: bool = False
    rule_indices: Optional[List[int]] = None


class ApplyRulesResult(BaseModel):
    processed: int
    modified: int
    details: List[Dict[str, Any]] = []
    message: Optional[str] = None
