from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.system_setting import SystemSetting
from app.models.user import User
from app.schemas.review import ContractExtractedFields, ReviewRiskItem
from app.schemas.system_setting import (
    SystemSettingsResponse,
    SystemSettingsTestRequest,
    SystemSettingsTestResponse,
    SystemSettingsUpdateRequest,
)
from app.services.permission_service import ensure_can_manage_system_settings
from app.services.review_log_service import create_review_log

SETTING_REVIEW_PROVIDER = "review_provider"
SETTING_LLM_BASE_URL = "llm_base_url"
SETTING_LLM_MODEL = "llm_model"
SETTING_LLM_API_KEY = "llm_api_key"
SETTING_LLM_TIMEOUT_SECONDS = "llm_timeout_seconds"
SETTING_LAST_TEST_SUCCESS = "llm_last_test_success"
SETTING_LAST_TEST_MESSAGE = "llm_last_test_message"
SETTING_LAST_TESTED_AT = "llm_last_tested_at"
SETTING_LAST_SUMMARY_CALL_SUCCESS = "llm_last_summary_call_success"
SETTING_LAST_SUMMARY_CALL_MESSAGE = "llm_last_summary_call_message"
SETTING_LAST_SUMMARY_CALLED_AT = "llm_last_summary_called_at"
SETTING_LAST_RISK_CALL_SUCCESS = "llm_last_risk_call_success"
SETTING_LAST_RISK_CALL_MESSAGE = "llm_last_risk_call_message"
SETTING_LAST_RISK_CALLED_AT = "llm_last_risk_called_at"


@dataclass
class ResolvedLlmSettings:
    review_provider: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_timeout_seconds: int


def _setting_map(db: Session) -> dict[str, SystemSetting]:
    return {
        item.setting_key: item
        for item in db.scalars(select(SystemSetting)).all()
    }


def _get_string(setting_map: dict[str, SystemSetting], key: str, default: str) -> str:
    setting = setting_map.get(key)
    if setting is None or setting.setting_value is None:
        return default
    return setting.setting_value


def _get_int(setting_map: dict[str, SystemSetting], key: str, default: int) -> int:
    setting = setting_map.get(key)
    if setting is None or setting.setting_value is None or setting.setting_value == "":
        return default
    try:
        return int(setting.setting_value)
    except ValueError:
        return default


def resolve_llm_settings(db: Session, defaults) -> ResolvedLlmSettings:
    setting_map = _setting_map(db)
    return ResolvedLlmSettings(
        review_provider=_get_string(setting_map, SETTING_REVIEW_PROVIDER, defaults.review_provider),
        llm_base_url=_get_string(setting_map, SETTING_LLM_BASE_URL, defaults.llm_base_url or ""),
        llm_api_key=_get_string(setting_map, SETTING_LLM_API_KEY, defaults.llm_api_key or ""),
        llm_model=_get_string(setting_map, SETTING_LLM_MODEL, defaults.llm_model or ""),
        llm_timeout_seconds=_get_int(setting_map, SETTING_LLM_TIMEOUT_SECONDS, defaults.llm_timeout_seconds),
    )


def get_system_settings(db: Session, actor: User, defaults) -> SystemSettingsResponse:
    ensure_can_manage_system_settings(actor)
    resolved = resolve_llm_settings(db, defaults)
    setting_map = _setting_map(db)
    llm_ready = bool(resolved.llm_base_url and resolved.llm_model and resolved.llm_api_key)
    effective_provider = (
        "mock"
        if resolved.review_provider == "mock" or not llm_ready
        else "openai_compatible"
    )
    if resolved.review_provider == "mock":
        status_message = "当前使用 mock 模式。"
    elif llm_ready:
        status_message = "当前已配置真实模型，审查时会启用 OpenAI 兼容 provider。"
    else:
        status_message = "已选择 openai_compatible，但配置尚不完整，运行时会降级为 mock。"
    return SystemSettingsResponse(
        review_provider=resolved.review_provider,
        llm_base_url=resolved.llm_base_url,
        llm_model=resolved.llm_model,
        llm_timeout_seconds=resolved.llm_timeout_seconds,
        llm_api_key_configured=bool(resolved.llm_api_key),
        effective_provider=effective_provider,
        llm_ready=llm_ready,
        status_message=status_message,
        last_test_success=(
            _get_string(setting_map, SETTING_LAST_TEST_SUCCESS, "").lower() == "true"
            if _get_string(setting_map, SETTING_LAST_TEST_SUCCESS, "") != ""
            else None
        ),
        last_test_message=_get_string(setting_map, SETTING_LAST_TEST_MESSAGE, "") or None,
        last_tested_at=_get_string(setting_map, SETTING_LAST_TESTED_AT, "") or None,
        last_summary_call_success=(
            _get_string(setting_map, SETTING_LAST_SUMMARY_CALL_SUCCESS, "").lower() == "true"
            if _get_string(setting_map, SETTING_LAST_SUMMARY_CALL_SUCCESS, "") != ""
            else None
        ),
        last_summary_call_message=_get_string(setting_map, SETTING_LAST_SUMMARY_CALL_MESSAGE, "") or None,
        last_summary_called_at=_get_string(setting_map, SETTING_LAST_SUMMARY_CALLED_AT, "") or None,
        last_risk_call_success=(
            _get_string(setting_map, SETTING_LAST_RISK_CALL_SUCCESS, "").lower() == "true"
            if _get_string(setting_map, SETTING_LAST_RISK_CALL_SUCCESS, "") != ""
            else None
        ),
        last_risk_call_message=_get_string(setting_map, SETTING_LAST_RISK_CALL_MESSAGE, "") or None,
        last_risk_called_at=_get_string(setting_map, SETTING_LAST_RISK_CALLED_AT, "") or None,
    )


def _upsert_setting(db: Session, key: str, value: str | None, *, is_secret: bool = False) -> None:
    setting = db.scalar(select(SystemSetting).where(SystemSetting.setting_key == key))
    if setting is None:
        db.add(SystemSetting(setting_key=key, setting_value=value, is_secret=is_secret))
        db.flush()
        return
    setting.setting_value = value
    setting.is_secret = is_secret


def update_system_settings(
    db: Session,
    payload: SystemSettingsUpdateRequest,
    actor: User,
    defaults,
) -> SystemSettingsResponse:
    ensure_can_manage_system_settings(actor)
    _upsert_setting(db, SETTING_REVIEW_PROVIDER, payload.review_provider)
    _upsert_setting(db, SETTING_LLM_BASE_URL, payload.llm_base_url.strip())
    _upsert_setting(db, SETTING_LLM_MODEL, payload.llm_model.strip())
    _upsert_setting(db, SETTING_LLM_TIMEOUT_SECONDS, str(payload.llm_timeout_seconds))

    if payload.clear_llm_api_key:
        _upsert_setting(db, SETTING_LLM_API_KEY, "", is_secret=True)
    elif payload.llm_api_key is not None and payload.llm_api_key.strip():
        _upsert_setting(db, SETTING_LLM_API_KEY, payload.llm_api_key.strip(), is_secret=True)

    create_review_log(
        db,
        operator_id=actor.id,
        target_type="system_setting",
        target_id=None,
        action_type="update_system_settings",
        action_detail=f"Updated provider={payload.review_provider}, model={payload.llm_model or '-'}",
    )
    db.commit()
    return get_system_settings(db, actor, defaults)


def test_system_settings(
    db: Session,
    payload: SystemSettingsTestRequest,
    actor: User,
    defaults,
) -> SystemSettingsTestResponse:
    ensure_can_manage_system_settings(actor)
    if payload.review_provider == "mock":
        result = SystemSettingsTestResponse(success=True, provider="mock", message="mock 模式无需连接测试。")
        _persist_test_result(db, actor, result)
        return result

    from app.services.openai_compatible_llm_service import (
        OpenAICompatibleRuntimeSettings,
        OpenAICompatibleLlmError,
        build_openai_compatible_summary_with_settings,
    )

    runtime = OpenAICompatibleRuntimeSettings(
        llm_base_url=payload.llm_base_url.strip(),
        llm_api_key=(payload.llm_api_key or "").strip(),
        llm_model=payload.llm_model.strip(),
        llm_timeout_seconds=payload.llm_timeout_seconds,
    )
    try:
        summary = build_openai_compatible_summary_with_settings(
            runtime,
            ContractExtractedFields(contract_name="系统设置测试合同", project_name="模型连通性测试"),
            [
                ReviewRiskItem(
                    code="connectivity_test",
                    title="连通性测试风险",
                    level="low",
                    matched_text="测试数据",
                    description="用于验证模型接口是否可用。",
                    recommendation="接口可用即可。",
                    source="rule",
                )
            ],
        )
    except OpenAICompatibleLlmError as exc:
        result = SystemSettingsTestResponse(success=False, provider=payload.review_provider, message=str(exc))
        _persist_test_result(db, actor, result)
        return result

    result = SystemSettingsTestResponse(
        success=True,
        provider=payload.review_provider,
        message=f"连接成功，模型返回示例摘要：{summary}",
    )
    _persist_test_result(db, actor, result)
    return result


def _persist_test_result(db: Session, actor: User, result: SystemSettingsTestResponse) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    _upsert_setting(db, SETTING_LAST_TEST_SUCCESS, "true" if result.success else "false")
    _upsert_setting(db, SETTING_LAST_TEST_MESSAGE, result.message)
    _upsert_setting(db, SETTING_LAST_TESTED_AT, timestamp)
    create_review_log(
        db,
        operator_id=actor.id,
        target_type="system_setting",
        target_id=None,
        action_type="test_system_settings",
        action_detail=f"Tested provider={result.provider}, success={result.success}",
    )
    db.commit()


def record_llm_runtime_result(
    db: Session,
    *,
    call_type: str,
    success: bool,
    message: str,
) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    if call_type == "summary":
        _upsert_setting(db, SETTING_LAST_SUMMARY_CALL_SUCCESS, "true" if success else "false")
        _upsert_setting(db, SETTING_LAST_SUMMARY_CALL_MESSAGE, message)
        _upsert_setting(db, SETTING_LAST_SUMMARY_CALLED_AT, timestamp)
        db.flush()
        return

    if call_type == "risk":
        _upsert_setting(db, SETTING_LAST_RISK_CALL_SUCCESS, "true" if success else "false")
        _upsert_setting(db, SETTING_LAST_RISK_CALL_MESSAGE, message)
        _upsert_setting(db, SETTING_LAST_RISK_CALLED_AT, timestamp)
        db.flush()
