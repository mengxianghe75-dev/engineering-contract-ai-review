from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_system_settings_access
from app.core.config import settings
from app.models.user import User
from app.schemas.system_setting import (
    SystemSettingsResponse,
    SystemSettingsTestRequest,
    SystemSettingsTestResponse,
    SystemSettingsUpdateRequest,
)
from app.services.system_setting_service import (
    get_system_settings,
    test_system_settings,
    update_system_settings,
)

router = APIRouter(prefix="/system-settings", tags=["system-settings"])


@router.get("", response_model=SystemSettingsResponse)
def get_system_settings_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_settings_access),
) -> SystemSettingsResponse:
    return get_system_settings(db, current_user, settings)


@router.patch("", response_model=SystemSettingsResponse)
def update_system_settings_endpoint(
    payload: SystemSettingsUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_settings_access),
) -> SystemSettingsResponse:
    return update_system_settings(db, payload, current_user, settings)


@router.post("/test", response_model=SystemSettingsTestResponse)
def test_system_settings_endpoint(
    payload: SystemSettingsTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_settings_access),
) -> SystemSettingsTestResponse:
    return test_system_settings(db, payload, current_user, settings)
