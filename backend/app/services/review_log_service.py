from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.review_log import ReviewLog
from app.models.user import User
from app.schemas.review_log import ReviewLogItem
from app.services.permission_service import ensure_can_manage_users


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def create_review_log(
    db: Session,
    *,
    operator_id: int | None,
    target_type: str,
    target_id: int | None,
    action_type: str,
    action_detail: str | None = None,
) -> ReviewLog:
    log = ReviewLog(
        operator_id=operator_id,
        target_type=target_type,
        target_id=target_id,
        action_type=action_type,
        action_detail=action_detail,
    )
    db.add(log)
    db.flush()
    return log


def serialize_review_log(log: ReviewLog, username_map: dict[int, str]) -> ReviewLogItem:
    return ReviewLogItem(
        id=log.id,
        operator_id=log.operator_id,
        operator_username=username_map.get(log.operator_id) if log.operator_id is not None else None,
        target_type=log.target_type,
        target_id=log.target_id,
        action_type=log.action_type,
        action_detail=log.action_detail,
        created_at=log.created_at.isoformat(),
    )


def list_review_logs(
    db: Session,
    actor: User,
    *,
    operator_id: int | None = None,
    action_type: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
) -> list[ReviewLogItem]:
    ensure_can_manage_users(actor)
    query = select(ReviewLog).order_by(ReviewLog.created_at.desc(), ReviewLog.id.desc())
    if operator_id is not None:
        query = query.where(ReviewLog.operator_id == operator_id)
    if action_type:
        query = query.where(ReviewLog.action_type == action_type)
    if created_from:
        query = query.where(ReviewLog.created_at >= _parse_datetime(created_from))
    if created_to:
        query = query.where(ReviewLog.created_at <= _parse_datetime(created_to))
    logs = db.scalars(query).all()
    operator_ids = {log.operator_id for log in logs if log.operator_id is not None}
    users = db.scalars(select(User).where(User.id.in_(operator_ids))).all() if operator_ids else []
    username_map = {user.id: user.username for user in users}
    return [serialize_review_log(log, username_map) for log in logs]
