from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.review_rule import ReviewRule
from app.models.user import User
from app.schemas.review_rule import ReviewRuleCreateRequest, ReviewRuleResponse, ReviewRuleUpdateRequest
from app.services.permission_service import ensure_can_manage_users
from app.services.review_log_service import create_review_log


def serialize_review_rule(rule: ReviewRule) -> ReviewRuleResponse:
    return ReviewRuleResponse(
        id=rule.id,
        name=rule.name,
        rule_code=rule.rule_code,
        risk_type=rule.risk_type,
        condition_type=rule.condition_type,
        condition_value=rule.condition_value,
        risk_level=rule.risk_level,
        suggestion=rule.suggestion,
        priority=rule.priority,
        is_active=rule.is_active,
        is_deleted=rule.is_deleted,
        contract_type_scope=rule.contract_type_scope,
        created_by=rule.created_by,
        created_at=rule.created_at.isoformat(),
        updated_at=rule.updated_at.isoformat(),
    )


def list_review_rules(db: Session, actor: User) -> list[ReviewRuleResponse]:
    ensure_can_manage_users(actor)
    rules = db.scalars(select(ReviewRule).order_by(ReviewRule.priority.asc(), ReviewRule.id.asc())).all()
    return [serialize_review_rule(rule) for rule in rules]


def create_review_rule(db: Session, payload: ReviewRuleCreateRequest, actor: User) -> ReviewRuleResponse:
    ensure_can_manage_users(actor)
    existing = db.scalar(select(ReviewRule).where(ReviewRule.rule_code == payload.rule_code))
    if existing is not None:
        raise ValueError("Rule code already exists.")
    rule = ReviewRule(
        name=payload.name,
        rule_code=payload.rule_code,
        risk_type=payload.risk_type,
        condition_type=payload.condition_type,
        condition_value=payload.condition_value,
        risk_level=payload.risk_level,
        suggestion=payload.suggestion,
        priority=payload.priority,
        is_active=payload.is_active,
        contract_type_scope=payload.contract_type_scope,
        created_by=actor.id,
    )
    db.add(rule)
    create_review_log(
        db,
        operator_id=actor.id,
        target_type="review_rule",
        target_id=None,
        action_type="create_rule",
        action_detail=f"Created rule {payload.rule_code}",
    )
    db.commit()
    db.refresh(rule)
    return serialize_review_rule(rule)


def update_review_rule(
    db: Session,
    rule_id: int,
    payload: ReviewRuleUpdateRequest,
    actor: User,
) -> ReviewRuleResponse:
    ensure_can_manage_users(actor)
    rule = db.scalar(select(ReviewRule).where(ReviewRule.id == rule_id))
    if rule is None:
        raise ValueError("Review rule not found.")
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(rule, field, value)
    detail = "Updated rule"
    if "is_active" in updates:
        detail = "Enabled rule" if updates["is_active"] else "Disabled rule"
    if updates.get("is_deleted"):
        detail = "Soft deleted rule"
    create_review_log(
        db,
        operator_id=actor.id,
        target_type="review_rule",
        target_id=rule.id,
        action_type="update_rule",
        action_detail=detail,
    )
    db.commit()
    db.refresh(rule)
    return serialize_review_rule(rule)
