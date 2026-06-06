from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_user_management_access
from app.models.user import User
from app.schemas.user import UserCreateRequest, UserListItem, UserResponse, UserUpdateRequest
from app.services.user_service import create_user, list_users, update_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserListItem])
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_management_access),
) -> list[UserListItem]:
    return list_users(db, current_user)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_management_access),
) -> UserResponse:
    try:
        return create_user(db, payload, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/{user_id}", response_model=UserResponse)
def update_user_endpoint(
    user_id: int,
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_management_access),
) -> UserResponse:
    try:
        return update_user(db, user_id, payload, current_user)
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if detail == "User not found." else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc
