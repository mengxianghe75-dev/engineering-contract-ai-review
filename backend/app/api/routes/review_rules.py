from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_user_management_access
from app.models.user import User
from app.schemas.review_rule import ReviewRuleCreateRequest, ReviewRuleResponse, ReviewRuleUpdateRequest
from app.services.review_rule_service import create_review_rule, list_review_rules, update_review_rule

router = APIRouter(prefix="/review-rules", tags=["review-rules"])


@router.get("", response_model=list[ReviewRuleResponse])
def get_review_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_management_access),
) -> list[ReviewRuleResponse]:
    return list_review_rules(db, current_user)


@router.post("", response_model=ReviewRuleResponse, status_code=status.HTTP_201_CREATED)
def create_review_rule_endpoint(
    payload: ReviewRuleCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_management_access),
) -> ReviewRuleResponse:
    try:
        return create_review_rule(db, payload, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/{rule_id}", response_model=ReviewRuleResponse)
def update_review_rule_endpoint(
    rule_id: int,
    payload: ReviewRuleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_management_access),
) -> ReviewRuleResponse:
    try:
        return update_review_rule(db, rule_id, payload, current_user)
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if detail == "Review rule not found." else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc
