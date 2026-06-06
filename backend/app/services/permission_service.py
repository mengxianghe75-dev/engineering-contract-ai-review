from fastapi import HTTPException, status

from app.models.user import User

ADMIN_ROLE = "admin"
REVIEWER_ROLE = "reviewer"
VIEWER_ROLE = "viewer"

ROLE_ORDER = [ADMIN_ROLE, REVIEWER_ROLE, VIEWER_ROLE]
ALL_ROLE_CODES = set(ROLE_ORDER)


def get_role_codes(user: User) -> list[str]:
    role_codes = {
        user_role.role.code
        for user_role in user.user_roles
        if user_role.role is not None
    }
    if user.is_admin:
        role_codes.add(ADMIN_ROLE)
    return [code for code in ROLE_ORDER if code in role_codes]


def normalize_role_codes(role_codes: list[str]) -> list[str]:
    normalized = []
    seen: set[str] = set()
    for code in role_codes:
        normalized_code = code.strip().lower()
        if normalized_code not in ALL_ROLE_CODES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported role: {code}",
            )
        if normalized_code not in seen:
            seen.add(normalized_code)
            normalized.append(normalized_code)
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one role is required.",
        )
    return normalized


def require_roles(user: User, allowed_roles: set[str], detail: str = "Permission denied.") -> None:
    if set(get_role_codes(user)) & allowed_roles:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def ensure_can_manage_users(user: User) -> None:
    require_roles(user, {ADMIN_ROLE}, "Only admin users can manage users.")


def ensure_can_manage_system_settings(user: User) -> None:
    require_roles(user, {ADMIN_ROLE}, "Only admin users can manage system settings.")


def ensure_can_view_contracts(user: User) -> None:
    require_roles(
        user,
        {ADMIN_ROLE, REVIEWER_ROLE, VIEWER_ROLE},
        "You do not have permission to view contracts.",
    )


def ensure_can_modify_contracts(user: User) -> None:
    require_roles(
        user,
        {ADMIN_ROLE, REVIEWER_ROLE},
        "You do not have permission to modify contracts.",
    )
