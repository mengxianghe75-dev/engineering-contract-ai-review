from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.user import User
from app.models.user_role import UserRole
from app.services.permission_service import (
    ensure_can_manage_system_settings,
    ensure_can_manage_users,
    ensure_can_modify_contracts,
    ensure_can_view_contracts,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
        ) from exc

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token payload.",
        )

    user = db.scalar(
        select(User)
        .options(joinedload(User.user_roles).joinedload(UserRole.role))
        .where(User.username == subject)
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found for access token.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive.",
        )
    return user


def require_user_management_access(current_user: User = Depends(get_current_user)) -> User:
    ensure_can_manage_users(current_user)
    return current_user


def require_system_settings_access(current_user: User = Depends(get_current_user)) -> User:
    ensure_can_manage_system_settings(current_user)
    return current_user


def require_contract_read_access(current_user: User = Depends(get_current_user)) -> User:
    ensure_can_view_contracts(current_user)
    return current_user


def require_contract_write_access(current_user: User = Depends(get_current_user)) -> User:
    ensure_can_modify_contracts(current_user)
    return current_user
