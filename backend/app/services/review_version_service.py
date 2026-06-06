from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.contract_file import ContractFile
from app.models.contract_review_result import ContractReviewResult
from app.models.review_version import ReviewVersion
from app.models.user import User
from app.schemas.review import ContractExtractedFields, ReviewRiskItem
from app.schemas.review_version import (
    ReviewVersionCompareResponse,
    ReviewVersionDetail,
    ReviewVersionFieldChange,
    ReviewVersionItem,
    ReviewVersionRuntimeChange,
    ReviewVersionRiskLevelChange,
    ReviewVersionRiskSnapshot,
)
from app.services.permission_service import ensure_can_view_contracts

FIELD_LABELS = {
    "contract_name": "合同名称",
    "contract_number": "合同编号",
    "project_name": "项目名称",
    "party_a": "甲方",
    "party_b": "乙方",
    "contract_type": "合同类型",
    "sign_date": "签订日期",
    "contract_amount": "合同金额",
    "construction_period": "工期",
    "payment_terms": "付款条款",
    "warranty_period": "质保期",
    "dispute_resolution": "争议解决",
    "breach_liability": "违约责任",
}


def compute_overall_risk_level(risks: list[ReviewRiskItem]) -> str:
    levels = {risk.level for risk in risks}
    if "high" in levels:
        return "high"
    if "medium" in levels:
        return "medium"
    return "low"


def create_review_version(
    db: Session,
    *,
    contract_id: int,
    triggered_by: int | None,
    trigger_source: str,
    extracted_fields: ContractExtractedFields,
    risks: list[ReviewRiskItem],
    summary: str,
    provider: str,
    summary_provider: str | None = None,
    summary_success: bool | None = None,
    summary_message: str | None = None,
    risk_provider: str | None = None,
    risk_success: bool | None = None,
    risk_message: str | None = None,
) -> ReviewVersion:
    current_max = db.scalar(
        select(func.max(ReviewVersion.version_no)).where(ReviewVersion.contract_id == contract_id)
    )
    version = ReviewVersion(
        contract_id=contract_id,
        version_no=(current_max or 0) + 1,
        triggered_by=triggered_by,
        trigger_source=trigger_source,
        extracted_fields=extracted_fields.model_dump(),
        risk_items=[risk.model_dump() for risk in risks],
        summary=summary,
        provider=provider,
        summary_provider=summary_provider,
        summary_success=summary_success,
        summary_message=summary_message,
        risk_provider=risk_provider,
        risk_success=risk_success,
        risk_message=risk_message,
        overall_risk_level=compute_overall_risk_level(risks),
    )
    db.add(version)
    db.flush()
    return version


def _contract_group_id(contract_file: ContractFile) -> int:
    return contract_file.version_root_id or contract_file.id


def _normalize_display_value(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "-"
    text = str(value).strip()
    return text or "-"


def _risk_key(item: dict) -> str:
    return f"{item.get('code', '')}:{item.get('title', '')}".lower()


def _runtime_display_value(value: object) -> str:
    if value is None:
        return "-"
    text = str(value).strip()
    return text or "-"


def _summary_runtime_label(version: ReviewVersion | None) -> str:
    if version is None:
        return "未执行"
    if version.summary_success is True:
        return f"成功 ({version.summary_provider or version.provider or '-'})"
    if version.summary_success is False:
        return f"失败/降级 ({version.summary_provider or version.provider or '-'})"
    return "未记录"


def _risk_runtime_label(version: ReviewVersion | None) -> str:
    if version is None:
        return "未执行"
    provider = version.risk_provider or "未启用"
    if version.risk_success is True:
        return f"成功 ({provider})"
    if version.risk_success is False:
        return f"失败/降级 ({provider})"
    return "未启用或未记录"


def _is_summary_degraded(version: ReviewVersion | None) -> bool:
    if version is None:
        return False
    return version.summary_success is False or (version.provider or "").strip() == "mock_fallback"


def _is_risk_degraded(version: ReviewVersion | None) -> bool:
    if version is None:
        return False
    return version.risk_success is False or (version.risk_provider or "").strip() == "mock_fallback"


def _load_contract_group(db: Session, contract_id: int) -> tuple[ContractFile, list[ContractFile]]:
    current_file = db.scalar(select(ContractFile).where(ContractFile.id == contract_id))
    if current_file is None:
        raise ValueError("Contract not found.")
    root_id = _contract_group_id(current_file)
    files = db.scalars(
        select(ContractFile)
        .where(ContractFile.version_root_id == root_id)
        .order_by(ContractFile.upload_version_no.desc(), ContractFile.id.desc())
    ).all()
    return current_file, files


def _load_review_maps(
    db: Session,
    contract_files: list[ContractFile],
) -> tuple[dict[int, ContractReviewResult], dict[int, ReviewVersion], dict[int, str]]:
    file_ids = [item.id for item in contract_files]
    review_results = db.scalars(
        select(ContractReviewResult).where(ContractReviewResult.contract_file_id.in_(file_ids))
    ).all() if file_ids else []
    review_result_map = {item.contract_file_id: item for item in review_results}
    latest_version_ids = [item.latest_version_id for item in review_results if item.latest_version_id is not None]
    latest_versions = db.scalars(select(ReviewVersion).where(ReviewVersion.id.in_(latest_version_ids))).all() if latest_version_ids else []
    latest_version_map = {item.id: item for item in latest_versions}
    trigger_ids = {item.triggered_by for item in latest_versions if item.triggered_by is not None}
    users = db.scalars(select(User).where(User.id.in_(trigger_ids))).all() if trigger_ids else []
    username_map = {user.id: user.username for user in users}
    return review_result_map, latest_version_map, username_map


def list_review_versions(db: Session, contract_id: int, actor: User) -> list[ReviewVersionItem]:
    ensure_can_view_contracts(actor)
    _, contract_files = _load_contract_group(db, contract_id)
    review_result_map, latest_version_map, username_map = _load_review_maps(db, contract_files)

    items: list[ReviewVersionItem] = []
    for contract_file in contract_files:
        review_result = review_result_map.get(contract_file.id)
        latest_review_version = (
            latest_version_map.get(review_result.latest_version_id)
            if review_result is not None and review_result.latest_version_id is not None
            else None
        )
        items.append(
            ReviewVersionItem(
                id=contract_file.id,
                contract_id=_contract_group_id(contract_file),
                version_no=contract_file.upload_version_no,
                file_id=contract_file.id,
                original_filename=contract_file.original_filename,
                latest_review_version_no=review_result.latest_version_no if review_result is not None else None,
                triggered_by=latest_review_version.triggered_by if latest_review_version is not None else None,
                triggered_by_username=(
                    username_map.get(latest_review_version.triggered_by)
                    if latest_review_version is not None and latest_review_version.triggered_by is not None
                    else None
                ),
                trigger_source=latest_review_version.trigger_source if latest_review_version is not None else "not_reviewed",
                summary=review_result.summary if review_result is not None else "该上传版本尚未执行审查。",
                provider=review_result.provider if review_result is not None else "not_reviewed",
                summary_provider=latest_review_version.summary_provider if latest_review_version is not None else None,
                summary_success=latest_review_version.summary_success if latest_review_version is not None else None,
                risk_provider=latest_review_version.risk_provider if latest_review_version is not None else None,
                risk_success=latest_review_version.risk_success if latest_review_version is not None else None,
                overall_risk_level=(
                    latest_review_version.overall_risk_level if latest_review_version is not None else "low"
                ),
                risk_count=len(review_result.risks or []) if review_result is not None else 0,
                created_at=contract_file.created_at.isoformat(),
            )
        )

    return items


def get_review_version_detail(db: Session, contract_id: int, version_id: int, actor: User) -> ReviewVersionDetail:
    ensure_can_view_contracts(actor)
    _, contract_files = _load_contract_group(db, contract_id)
    contract_file = next((item for item in contract_files if item.id == version_id), None)
    if contract_file is None:
        raise ValueError("Review version not found.")

    review_result = db.scalar(
        select(ContractReviewResult).where(ContractReviewResult.contract_file_id == contract_file.id)
    )
    latest_review_version = None
    triggered_by_username = None
    if review_result is not None and review_result.latest_version_id is not None:
        latest_review_version = db.scalar(select(ReviewVersion).where(ReviewVersion.id == review_result.latest_version_id))
        if latest_review_version is not None and latest_review_version.triggered_by is not None:
            triggered_by_username = db.scalar(select(User.username).where(User.id == latest_review_version.triggered_by))

    return ReviewVersionDetail(
        id=contract_file.id,
        contract_id=_contract_group_id(contract_file),
        version_no=contract_file.upload_version_no,
        file_id=contract_file.id,
        original_filename=contract_file.original_filename,
        review_status="completed" if review_result is not None else "pending",
        triggered_by=latest_review_version.triggered_by if latest_review_version is not None else None,
        triggered_by_username=triggered_by_username,
        trigger_source=latest_review_version.trigger_source if latest_review_version is not None else "not_reviewed",
        extracted_fields=review_result.extracted_fields if review_result is not None else {},
        risk_items=review_result.risks if review_result is not None else [],
        summary=review_result.summary if review_result is not None else "该上传版本尚未执行审查。",
        provider=review_result.provider if review_result is not None else "not_reviewed",
        summary_provider=latest_review_version.summary_provider if latest_review_version is not None else None,
        summary_success=latest_review_version.summary_success if latest_review_version is not None else None,
        summary_message=latest_review_version.summary_message if latest_review_version is not None else None,
        risk_provider=latest_review_version.risk_provider if latest_review_version is not None else None,
        risk_success=latest_review_version.risk_success if latest_review_version is not None else None,
        risk_message=latest_review_version.risk_message if latest_review_version is not None else None,
        overall_risk_level=latest_review_version.overall_risk_level if latest_review_version is not None else "low",
        created_at=contract_file.created_at.isoformat(),
    )


def compare_review_versions(
    db: Session,
    contract_id: int,
    base_version_id: int,
    target_version_id: int,
    actor: User,
) -> ReviewVersionCompareResponse:
    ensure_can_view_contracts(actor)
    _, contract_files = _load_contract_group(db, contract_id)
    file_map = {item.id: item for item in contract_files}
    base_file = file_map.get(base_version_id)
    target_file = file_map.get(target_version_id)
    if base_file is None or target_file is None:
        raise ValueError("Review version not found.")
    if base_file.id == target_file.id:
        raise ValueError("Please select two different review versions.")

    base_result = db.scalar(select(ContractReviewResult).where(ContractReviewResult.contract_file_id == base_file.id))
    target_result = db.scalar(select(ContractReviewResult).where(ContractReviewResult.contract_file_id == target_file.id))
    base_latest = (
        db.scalar(select(ReviewVersion).where(ReviewVersion.id == base_result.latest_version_id))
        if base_result is not None and base_result.latest_version_id is not None
        else None
    )
    target_latest = (
        db.scalar(select(ReviewVersion).where(ReviewVersion.id == target_result.latest_version_id))
        if target_result is not None and target_result.latest_version_id is not None
        else None
    )

    base_fields = base_result.extracted_fields if base_result is not None else {}
    target_fields = target_result.extracted_fields if target_result is not None else {}

    field_changes: list[ReviewVersionFieldChange] = []
    for field, label in FIELD_LABELS.items():
        before_value = _normalize_display_value(base_fields.get(field))
        after_value = _normalize_display_value(target_fields.get(field))
        if before_value == after_value:
            continue
        field_changes.append(
            ReviewVersionFieldChange(
                field=field,
                label=label,
                before_value=before_value,
                after_value=after_value,
            )
        )

    runtime_changes: list[ReviewVersionRuntimeChange] = []
    runtime_pairs = (
        ("最终 provider", _runtime_display_value(base_result.provider if base_result is not None else "not_reviewed"), _runtime_display_value(target_result.provider if target_result is not None else "not_reviewed")),
        ("摘要状态", _summary_runtime_label(base_latest), _summary_runtime_label(target_latest)),
        ("风险补充状态", _risk_runtime_label(base_latest), _risk_runtime_label(target_latest)),
        ("摘要说明", _runtime_display_value(base_latest.summary_message if base_latest is not None else None), _runtime_display_value(target_latest.summary_message if target_latest is not None else None)),
        ("风险补充说明", _runtime_display_value(base_latest.risk_message if base_latest is not None else None), _runtime_display_value(target_latest.risk_message if target_latest is not None else None)),
    )
    for label, before_value, after_value in runtime_pairs:
        if before_value == after_value:
            continue
        runtime_changes.append(
            ReviewVersionRuntimeChange(
                label=label,
                before_value=before_value,
                after_value=after_value,
            )
        )

    summary_degraded = not _is_summary_degraded(base_latest) and _is_summary_degraded(target_latest)
    risk_degraded = not _is_risk_degraded(base_latest) and _is_risk_degraded(target_latest)
    summary_recovered = _is_summary_degraded(base_latest) and not _is_summary_degraded(target_latest)
    risk_recovered = _is_risk_degraded(base_latest) and not _is_risk_degraded(target_latest)
    degradation_events: list[str] = []
    recovery_events: list[str] = []
    if summary_degraded:
        degradation_events.append(
            f"摘要链路发生降级：V{base_file.upload_version_no} 为 {_summary_runtime_label(base_latest)}，"
            f"V{target_file.upload_version_no} 为 {_summary_runtime_label(target_latest)}"
        )
    if risk_degraded:
        degradation_events.append(
            f"风险补充链路发生降级：V{base_file.upload_version_no} 为 {_risk_runtime_label(base_latest)}，"
            f"V{target_file.upload_version_no} 为 {_risk_runtime_label(target_latest)}"
        )
    if summary_recovered:
        recovery_events.append(
            f"摘要链路恢复正常：V{base_file.upload_version_no} 为 {_summary_runtime_label(base_latest)}，"
            f"V{target_file.upload_version_no} 为 {_summary_runtime_label(target_latest)}"
        )
    if risk_recovered:
        recovery_events.append(
            f"风险补充链路恢复正常：V{base_file.upload_version_no} 为 {_risk_runtime_label(base_latest)}，"
            f"V{target_file.upload_version_no} 为 {_risk_runtime_label(target_latest)}"
        )

    base_risks = {_risk_key(item): item for item in ((base_result.risks if base_result is not None else []) or [])}
    target_risks = {_risk_key(item): item for item in ((target_result.risks if target_result is not None else []) or [])}
    added_risks: list[ReviewVersionRiskSnapshot] = []
    removed_risks: list[ReviewVersionRiskSnapshot] = []
    level_changed_risks: list[ReviewVersionRiskLevelChange] = []

    for key, risk in target_risks.items():
        if key not in base_risks:
            added_risks.append(
                ReviewVersionRiskSnapshot(
                    code=risk.get("code", ""),
                    title=risk.get("title", ""),
                    level=risk.get("level", "low"),
                    source=risk.get("source"),
                )
            )
            continue
        base_risk = base_risks[key]
        if (base_risk.get("level") or "low") != (risk.get("level") or "low"):
            level_changed_risks.append(
                ReviewVersionRiskLevelChange(
                    code=risk.get("code", ""),
                    title=risk.get("title", ""),
                    before_level=base_risk.get("level", "low"),
                    after_level=risk.get("level", "low"),
                    source=risk.get("source"),
                )
            )

    for key, risk in base_risks.items():
        if key in target_risks:
            continue
        removed_risks.append(
            ReviewVersionRiskSnapshot(
                code=risk.get("code", ""),
                title=risk.get("title", ""),
                level=risk.get("level", "low"),
                source=risk.get("source"),
            )
        )

    return ReviewVersionCompareResponse(
        contract_id=_contract_group_id(base_file),
        base_version_id=base_file.id,
        base_version_no=base_file.upload_version_no,
        target_version_id=target_file.id,
        target_version_no=target_file.upload_version_no,
        summary_changed=(base_result.summary if base_result is not None else "").strip()
        != (target_result.summary if target_result is not None else "").strip(),
        runtime_changed=bool(runtime_changes),
        summary_degraded=summary_degraded,
        risk_degraded=risk_degraded,
        degradation_events=degradation_events,
        summary_recovered=summary_recovered,
        risk_recovered=risk_recovered,
        recovery_events=recovery_events,
        runtime_changes=runtime_changes,
        field_changes=field_changes,
        added_risks=added_risks,
        removed_risks=removed_risks,
        level_changed_risks=level_changed_risks,
    )
