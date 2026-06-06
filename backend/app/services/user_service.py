from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.auth import AuthUserProfile
from app.schemas.user import UserCreateRequest, UserListItem, UserResponse, UserUpdateRequest
from app.services.permission_service import ADMIN_ROLE, get_role_codes, normalize_role_codes, ensure_can_manage_users
from app.services.review_log_service import create_review_log

ROLE_DEFINITIONS = {
    ADMIN_ROLE: {"name": "管理员", "description": "拥有全部权限"},
    "reviewer": {"name": "审查员", "description": "可上传、审查、查看合同"},
    "viewer": {"name": "查看者", "description": "仅可查看合同"},
}


def ensure_system_roles(db: Session) -> None:
    existing_roles = {
        role.code: role
        for role in db.scalars(select(Role)).all()
    }
    changed = False
    for code, meta in ROLE_DEFINITIONS.items():
        role = existing_roles.get(code)
        if role is None:
            db.add(Role(code=code, name=meta["name"], description=meta["description"]))
            changed = True
        elif role.name != meta["name"] or role.description != meta["description"]:
            role.name = meta["name"]
            role.description = meta["description"]
            changed = True
    if changed:
        db.flush()


def _get_roles_by_codes(db: Session, role_codes: list[str]) -> list[Role]:
    normalized_codes = normalize_role_codes(role_codes)
    roles = db.scalars(select(Role).where(Role.code.in_(normalized_codes))).all()
    roles_by_code = {role.code: role for role in roles}
    missing_codes = [code for code in normalized_codes if code not in roles_by_code]
    if missing_codes:
        raise ValueError(f"Roles not initialized: {', '.join(missing_codes)}")
    return [roles_by_code[code] for code in normalized_codes]


def _sync_user_roles(db: Session, user: User, role_codes: list[str]) -> None:
    roles = _get_roles_by_codes(db, role_codes)
    target_role_ids = {role.id for role in roles}
    existing_links = list(user.user_roles)

    for link in existing_links:
        if link.role_id not in target_role_ids:
            user.user_roles.remove(link)

    existing_role_ids = {link.role_id for link in user.user_roles}
    for role in roles:
        if role.id in existing_role_ids:
            continue
        user.user_roles.append(UserRole(role=role))

    user.is_admin = ADMIN_ROLE in [role.code for role in roles]


def serialize_user(user: User) -> UserResponse:
    role_codes = get_role_codes(user)
    return UserResponse(
        id=user.id,
        username=user.username,
        is_active=user.is_active,
        roles=role_codes,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )


def build_auth_user_profile(user: User) -> AuthUserProfile:
    return AuthUserProfile(
        id=user.id,
        username=user.username,
        is_active=user.is_active,
        roles=get_role_codes(user),
    )


def ensure_default_admin(db: Session) -> None:
    ensure_system_roles(db)
    admin = db.scalar(select(User).where(User.username == settings.default_admin_username))
    if admin is None:
        admin = User(
            username=settings.default_admin_username,
            password_hash=get_password_hash(settings.default_admin_password),
            is_admin=True,
            is_active=True,
        )
        db.add(admin)
        db.flush()

    _sync_user_roles(db, admin, [ADMIN_ROLE])
    db.commit()


def list_users(db: Session, actor: User) -> list[UserListItem]:
    ensure_can_manage_users(actor)
    users = db.scalars(select(User).order_by(User.created_at.desc(), User.id.desc())).all()
    return [
        UserListItem(
            id=user.id,
            username=user.username,
            is_active=user.is_active,
            roles=get_role_codes(user),
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
        )
        for user in users
    ]


def create_user(db: Session, payload: UserCreateRequest, actor: User) -> UserResponse:
    ensure_can_manage_users(actor)
    ensure_system_roles(db)

    existing_user = db.scalar(select(User).where(User.username == payload.username))
    if existing_user is not None:
        raise ValueError("Username already exists.")

    user = User(
        username=payload.username,
        password_hash=get_password_hash(payload.password),
        is_active=payload.is_active,
        is_admin=False,
    )
    db.add(user)
    db.flush()
    _sync_user_roles(db, user, payload.role_codes)
    create_review_log(
        db,
        operator_id=actor.id,
        target_type="user",
        target_id=user.id,
        action_type="create_user",
        action_detail=f"Created user {user.username}",
    )
    db.commit()
    db.refresh(user)
    return serialize_user(user)


def update_user(db: Session, user_id: int, payload: UserUpdateRequest, actor: User) -> UserResponse:
    ensure_can_manage_users(actor)
    ensure_system_roles(db)

    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise ValueError("User not found.")

    if payload.username and payload.username != user.username:
        existing_user = db.scalar(select(User).where(User.username == payload.username))
        if existing_user is not None:
            raise ValueError("Username already exists.")
        user.username = payload.username

    if payload.password:
        user.password_hash = get_password_hash(payload.password)
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.role_codes is not None:
        _sync_user_roles(db, user, payload.role_codes)

    detail = "Updated user profile"
    if payload.is_active is not None:
        detail = "Enabled user" if payload.is_active else "Disabled user"
    create_review_log(
        db,
        operator_id=actor.id,
        target_type="user",
        target_id=user.id,
        action_type="update_user",
        action_detail=detail,
    )
    db.commit()
    db.refresh(user)
    return serialize_user(user)
