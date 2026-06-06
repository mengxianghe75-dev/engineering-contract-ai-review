from __future__ import annotations

import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.review_rule import ReviewRule
from app.schemas.review import ContractExtractedFields, ReviewMatchDetail, ReviewRiskItem


def _parse_scope(scope: str | None) -> list[str]:
    if not scope:
        return []
    try:
        parsed = json.loads(scope)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        pass
    return [item.strip() for item in scope.split(",") if item.strip()]


def _parse_condition_values(condition_type: str, condition_value: str) -> list[str]:
    if condition_type in {"contains_any", "contains_all"}:
        try:
            parsed = json.loads(condition_value)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass
        return [item.strip() for item in re.split(r"[,\n]+", condition_value) if item.strip()]
    return [condition_value]


def _scope_matches(rule: ReviewRule, fields: ContractExtractedFields) -> bool:
    scopes = _parse_scope(rule.contract_type_scope)
    if not scopes:
        return True
    contract_type = (fields.contract_type or "").strip()
    return contract_type in scopes


def _match_rule(rule: ReviewRule, raw_text: str) -> str | None:
    values = _parse_condition_values(rule.condition_type, rule.condition_value)
    if rule.condition_type == "keyword":
        keyword = values[0]
        return keyword if keyword in raw_text else None
    if rule.condition_type == "regex":
        match = re.search(values[0], raw_text, flags=re.MULTILINE)
        return match.group(0) if match else None
    if rule.condition_type == "contains_any":
        matched = next((value for value in values if value in raw_text), None)
        return matched
    if rule.condition_type == "contains_all":
        return " && ".join(values) if values and all(value in raw_text for value in values) else None
    return None


def list_active_review_rules(db: Session) -> list[ReviewRule]:
    return db.scalars(
        select(ReviewRule)
        .where(ReviewRule.is_active.is_(True), ReviewRule.is_deleted.is_(False))
        .order_by(ReviewRule.priority.asc(), ReviewRule.id.asc())
    ).all()


def evaluate_review_rules(
    db: Session,
    raw_text: str,
    fields: ContractExtractedFields,
) -> list[ReviewRiskItem]:
    risks: list[ReviewRiskItem] = []
    rules = list_active_review_rules(db)
    for rule in rules:
        if not _scope_matches(rule, fields):
            continue
        matched_text = _match_rule(rule, raw_text)
        if not matched_text:
            continue
        risks.append(
            ReviewRiskItem(
                code=rule.rule_code,
                title=rule.name,
                level=rule.risk_level,
                matched_text=matched_text,
                description=rule.risk_type,
                recommendation=rule.suggestion,
                source="rule",
                rule_id=rule.id,
                match_detail=ReviewMatchDetail(
                    condition_type=rule.condition_type,
                    condition_value=rule.condition_value,
                    priority=rule.priority,
                    text_span=matched_text,
                ),
            )
        )
    return risks
