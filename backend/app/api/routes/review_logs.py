from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_user_management_access
from app.models.user import User
from app.schemas.review_log import ReviewLogItem
from app.services.review_log_service import list_review_logs

router = APIRouter(prefix="/review-logs", tags=["review-logs"])


@router.get("", response_model=list[ReviewLogItem])
def get_review_logs(
    operator_id: Optional[int] = Query(default=None),
    action_type: Optional[str] = Query(default=None),
    created_from: Optional[str] = Query(default=None),
    created_to: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_management_access),
) -> list[ReviewLogItem]:
    return list_review_logs(
        db,
        current_user,
        operator_id=operator_id,
        action_type=action_type,
        created_from=created_from,
        created_to=created_to,
    )
