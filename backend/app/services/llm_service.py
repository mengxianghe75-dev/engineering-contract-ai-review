from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.review import ContractExtractedFields, ReviewMatchDetail, ReviewRiskItem
from app.services.mock_llm_service import build_mock_summary
from app.services.openai_compatible_llm_service import (
    OpenAICompatibleLlmError,
    OpenAICompatibleRuntimeSettings,
    build_openai_compatible_risk_supplements_with_settings,
    build_openai_compatible_summary_with_settings,
)
from app.services.system_setting_service import record_llm_runtime_result, resolve_llm_settings


@dataclass(frozen=True)
class LlmSummaryRuntimeResult:
    summary: str
    provider: str
    success: bool
    message: str


@dataclass(frozen=True)
class LlmRiskRuntimeResult:
    risks: list[ReviewRiskItem]
    provider: str | None
    success: bool | None
    message: str


def generate_review_summary_with_provider(
    db: Session,
    fields: ContractExtractedFields,
    risks: list[ReviewRiskItem],
) -> LlmSummaryRuntimeResult:
    runtime = resolve_llm_settings(db, settings)
    provider = runtime.review_provider
    if provider == "mock":
        message = "mock provider generated summary"
        record_llm_runtime_result(db, call_type="summary", success=True, message=message)
        return LlmSummaryRuntimeResult(
            summary=build_mock_summary(fields, risks),
            provider="mock",
            success=True,
            message=message,
        )

    if provider == "openai_compatible":
        try:
            summary = build_openai_compatible_summary_with_settings(
                OpenAICompatibleRuntimeSettings(
                    llm_base_url=runtime.llm_base_url,
                    llm_api_key=runtime.llm_api_key,
                    llm_model=runtime.llm_model,
                    llm_timeout_seconds=runtime.llm_timeout_seconds,
                ),
                fields,
                risks,
            )
            message = f"openai_compatible summary succeeded with model={runtime.llm_model}"
            record_llm_runtime_result(db, call_type="summary", success=True, message=message)
            return LlmSummaryRuntimeResult(
                summary=summary,
                provider="openai_compatible",
                success=True,
                message=message,
            )
        except OpenAICompatibleLlmError:
            message = f"openai_compatible summary failed; fallback to mock with model={runtime.llm_model or '-'}"
            record_llm_runtime_result(db, call_type="summary", success=False, message=message)
            return LlmSummaryRuntimeResult(
                summary=build_mock_summary(fields, risks),
                provider="mock_fallback",
                success=False,
                message=message,
            )

    message = f"unsupported provider={provider}; fallback to mock"
    record_llm_runtime_result(db, call_type="summary", success=False, message=message)
    return LlmSummaryRuntimeResult(
        summary=build_mock_summary(fields, risks),
        provider="mock_fallback",
        success=False,
        message=message,
    )


def generate_llm_risk_supplements(
    db: Session,
    raw_text: str,
    fields: ContractExtractedFields,
    existing_risks: list[ReviewRiskItem],
) -> LlmRiskRuntimeResult:
    runtime = resolve_llm_settings(db, settings)
    if runtime.review_provider != "openai_compatible":
        message = f"risk supplement skipped because provider={runtime.review_provider}"
        record_llm_runtime_result(db, call_type="risk", success=True, message=message)
        return LlmRiskRuntimeResult(risks=[], provider=None, success=None, message=message)

    try:
        payload_items = build_openai_compatible_risk_supplements_with_settings(
            OpenAICompatibleRuntimeSettings(
                llm_base_url=runtime.llm_base_url,
                llm_api_key=runtime.llm_api_key,
                llm_model=runtime.llm_model,
                llm_timeout_seconds=runtime.llm_timeout_seconds,
            ),
            raw_text,
            fields,
            existing_risks,
        )
    except OpenAICompatibleLlmError:
        message = f"openai_compatible risk supplement failed with model={runtime.llm_model or '-'}"
        record_llm_runtime_result(db, call_type="risk", success=False, message=message)
        return LlmRiskRuntimeResult(
            risks=[],
            provider="mock_fallback",
            success=False,
            message=message,
        )

    normalized: list[ReviewRiskItem] = []
    seen_codes: set[str] = set()
    for item in payload_items[:3]:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip().lower()
        title = str(item.get("title") or "").strip()
        level = str(item.get("level") or "").strip().lower()
        description = str(item.get("description") or "").strip()
        recommendation = str(item.get("recommendation") or "").strip()
        matched_text = str(item.get("matched_text") or "").strip() or None
        if not code or not title or level not in {"high", "medium", "low"}:
            continue
        if not description or not recommendation or code in seen_codes:
            continue
        seen_codes.add(code)
        normalized.append(
            ReviewRiskItem(
                code=code,
                title=title,
                level=level,
                matched_text=matched_text,
                description=description,
                recommendation=recommendation,
                source="llm",
                match_detail=ReviewMatchDetail(
                    condition_type="llm_json",
                    condition_value=code,
                    text_span=matched_text,
                ),
            )
        )

    message = f"openai_compatible risk supplement returned {len(normalized)} items with model={runtime.llm_model}"
    record_llm_runtime_result(db, call_type="risk", success=True, message=message)
    return LlmRiskRuntimeResult(
        risks=normalized,
        provider="openai_compatible",
        success=True,
        message=message,
    )
