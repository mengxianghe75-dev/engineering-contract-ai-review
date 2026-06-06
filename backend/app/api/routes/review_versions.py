from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_contract_read_access
from app.models.user import User
from app.schemas.review_version import ReviewVersionCompareResponse, ReviewVersionDetail, ReviewVersionItem
from app.services.review_version_service import compare_review_versions, get_review_version_detail, list_review_versions

router = APIRouter(prefix="/contracts/{contract_id}/versions", tags=["review-versions"])


@router.get("", response_model=list[ReviewVersionItem])
def get_versions(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_contract_read_access),
) -> list[ReviewVersionItem]:
    try:
        return list_review_versions(db, contract_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/compare/result", response_model=ReviewVersionCompareResponse)
def compare_versions(
    contract_id: int,
    base_version_id: int,
    target_version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_contract_read_access),
) -> ReviewVersionCompareResponse:
    try:
        return compare_review_versions(db, contract_id, base_version_id, target_version_id, current_user)
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if detail in {"Review version not found.", "Contract not found."} else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc


@router.get("/{version_id}", response_model=ReviewVersionDetail)
def get_version_detail(
    contract_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_contract_read_access),
) -> ReviewVersionDetail:
    try:
        return get_review_version_detail(db, contract_id, version_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
