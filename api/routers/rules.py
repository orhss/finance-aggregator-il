"""Rules endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import CurrentUser, get_rules_service
from api.schemas.common import MessageResponse
from api.schemas.rules import ApplyRulesRequest, ApplyRulesResult, RuleCreate, RuleResponse
from services.rules_service import RulesService

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=List[RuleResponse])
def list_rules(
    _: str = CurrentUser,
    svc: RulesService = Depends(get_rules_service),
):
    return [
        RuleResponse(
            pattern=r.pattern,
            match_type=r.match_type.value,
            category=r.category,
            tags=r.tags,
            remove_tags=r.remove_tags,
            description=r.description,
            enabled=r.enabled,
        )
        for r in svc.get_rules()
    ]


@router.post("", response_model=RuleResponse)
def create_rule(
    body: RuleCreate,
    _: str = CurrentUser,
    svc: RulesService = Depends(get_rules_service),
):
    from services.rules_service import MatchType
    try:
        mt = MatchType(body.match_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid match_type: {body.match_type}")

    rule = svc.add_rule(
        pattern=body.pattern,
        category=body.category,
        tags=body.tags,
        remove_tags=body.remove_tags,
        match_type=mt,
        description=body.description,
    )
    return RuleResponse(
        pattern=rule.pattern,
        match_type=rule.match_type.value,
        category=rule.category,
        tags=rule.tags,
        remove_tags=rule.remove_tags,
        description=rule.description,
        enabled=rule.enabled,
    )


@router.delete("/{pattern}", response_model=MessageResponse)
def delete_rule(
    pattern: str,
    _: str = CurrentUser,
    svc: RulesService = Depends(get_rules_service),
):
    removed = svc.remove_rule(pattern)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rule with pattern '{pattern}' not found")
    return MessageResponse(message=f"Rule deleted: {pattern}")


@router.post("/apply", response_model=ApplyRulesResult)
def apply_rules(
    body: ApplyRulesRequest,
    _: str = CurrentUser,
    svc: RulesService = Depends(get_rules_service),
):
    result = svc.apply_rules(
        transaction_ids=body.transaction_ids,
        only_uncategorized=body.only_uncategorized,
        dry_run=body.dry_run,
        rule_indices=body.rule_indices,
    )
    return ApplyRulesResult(**result)
