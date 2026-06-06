from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.models.contract_file import ContractFile
from app.models.contract_parse_result import ContractParseResult
from app.models.contract_review_result import ContractReviewResult
from app.models.review_version import ReviewVersion
from app.models.user import User
from app.schemas.review import (
    ContractExtractedFields,
    ContractReviewResponse,
    ReviewMatchDetail,
    ReviewRiskItem,
)
from app.services.llm_service import (
    LlmSummaryRuntimeResult,
    generate_llm_risk_supplements,
    generate_review_summary_with_provider,
)
from app.services.permission_service import ensure_can_modify_contracts
from app.services.review_log_service import create_review_log
from app.services.review_version_service import create_review_version
from app.services.rule_engine_service import evaluate_review_rules


@dataclass(frozen=True)
class BuiltinHeuristicRule:
    code: str
    title: str
    level: str
    keywords: tuple[str, ...]
    negative_keywords: tuple[str, ...]
    description: str
    recommendation: str


BUILTIN_HEURISTIC_RULES: tuple[BuiltinHeuristicRule, ...] = (
    BuiltinHeuristicRule(
        code="payment_terms_risk",
        title="付款条款风险",
        level="high",
        keywords=("结清", "竣工验收合格后支付", "无预付款", "甲方审核后支付"),
        negative_keywords=("已支付预付款", "含预付款", "按月进度款", "节点支付"),
        description="付款条件偏严或付款节点不明确，可能导致回款滞后。",
        recommendation="补充预付款、进度款和付款时间上限，明确逾期付款责任。",
    ),
    BuiltinHeuristicRule(
        code="settlement_terms_risk",
        title="结算条款风险",
        level="medium",
        keywords=("最终结算以甲方审定为准", "结算以审计结果为准", "另行协商"),
        negative_keywords=("结算周期", "结算资料"),
        description="结算依据单方控制或结算周期不清，存在价款争议风险。",
        recommendation="明确结算资料、审核期限和逾期视为认可规则。",
    ),
    BuiltinHeuristicRule(
        code="schedule_liability_risk",
        title="工期责任风险",
        level="high",
        keywords=("每延误一日", "工期不得顺延", "自行承担赶工"),
        negative_keywords=("顺延", "不可抗力"),
        description="工期责任偏重乙方，且缺少顺延或免责条件。",
        recommendation="增加顺延条件、甲方原因停工处理和不可抗力条款。",
    ),
    BuiltinHeuristicRule(
        code="unbalanced_breach_liability",
        title="违约责任不对等",
        level="high",
        keywords=("乙方承担全部责任", "甲方不承担任何责任", "乙方单方违约"),
        negative_keywords=("双方", "甲方逾期付款"),
        description="违约责任明显偏向一方，存在责任失衡风险。",
        recommendation="补充甲方违约责任和双方对等责任机制。",
    ),
    BuiltinHeuristicRule(
        code="retention_money_risk",
        title="质保金风险",
        level="medium",
        keywords=("质保金", "保修金"),
        negative_keywords=("返还期限", "无息返还", "返还时间"),
        description="存在质保金约定但返还条件或期限不明。",
        recommendation="明确质保金比例、返还时间和返还前提。",
    ),
    BuiltinHeuristicRule(
        code="invoice_tax_risk",
        title="发票税务风险",
        level="medium",
        keywords=("提供发票后付款", "税率调整由乙方承担", "专票"),
        negative_keywords=("税率变化协商",),
        description="发票和税务责任分配不清，可能影响实际回款。",
        recommendation="明确开票类型、开票时间和税率变化处理机制。",
    ),
    BuiltinHeuristicRule(
        code="dispute_resolution_risk",
        title="争议解决风险",
        level="medium",
        keywords=("甲方所在地人民法院", "提交甲方所在地法院", "仲裁委员会"),
        negative_keywords=("工程所在地", "合同签订地", "双方协商"),
        description="争议解决地点对一方明显不利或条款不完整。",
        recommendation="优先约定工程所在地或合同履行地争议解决方式。",
    ),
    BuiltinHeuristicRule(
        code="scope_unclear_risk",
        title="工作范围不清",
        level="high",
        keywords=("详见附件", "以现场要求为准", "甲方通知为准"),
        negative_keywords=("工作内容", "承包范围", "工程范围"),
        description="工作范围表述不够清晰，易引发增项和责任争议。",
        recommendation="列明具体工作内容、边界和排除项。",
    ),
    BuiltinHeuristicRule(
        code="missing_change_order_clause",
        title="变更签证条款缺失",
        level="high",
        keywords=("变更", "签证"),
        negative_keywords=("变更程序", "书面签证", "签证确认"),
        description="变更签证流程不足，存在增减项无法确认的风险。",
        recommendation="补充变更申请、签证确认和价款调整流程。",
    ),
    BuiltinHeuristicRule(
        code="termination_clause_risk",
        title="合同解除条款风险",
        level="medium",
        keywords=("甲方有权解除", "单方解除"),
        negative_keywords=("解除条件", "解除通知", "结算方式"),
        description="解除权约定偏单方或解除后处理不清。",
        recommendation="明确双方解除条件、通知期限和解除后结算规则。",
    ),
)

CHAR_NORMALIZATION_MAP = str.maketrans(
    {
        "⼯": "工",
        "⽅": "方",
        "⽬": "目",
        "⽇": "日",
        "⽉": "月",
        "⼀": "一",
        "⼄": "乙",
        "⼈": "人",
        "⺠": "民",
        "⾦": "金",
        "¥": "￥",
    }
)


FIELD_PATTERNS: dict[str, tuple[str, ...]] = {
    "contract_name": (r"(?:合同名称|合同标题)[:：]\s*(.+)", r"^\s*(.+合同)\s*$"),
    "contract_number": (r"(?:合同编号|编号)[:：]\s*([A-Za-z0-9\-_（）()]+)",),
    "project_name": (r"(?:项目名称|工程名称)[:：]\s*(.+)",),
    "party_a": (r"(?:甲方|发包人|建设单位)[:：]\s*(.+)",),
    "party_b": (r"(?:乙方|承包人|施工单位)[:：]\s*(.+)",),
    "contract_type": (r"(?:合同类型|合同类别)[:：]\s*(.+)",),
    "sign_date": (r"(?:签订日期|签约日期|签订时间)[:：]\s*(.+)", r"(\d{4}年\d{1,2}月\d{1,2}日)"),
    "contract_amount": (r"(?:合同金额|含税合同价|签约合同价)[:：]\s*(.+)",),
    "construction_period": (r"(?:工期|总工期|履约期限)[:：]\s*(.+)",),
    "payment_terms": (r"(?:付款条款|付款方式|支付方式)[:：]\s*(.+)",),
    "warranty_period": (r"(?:质保期|保修期)[:：]\s*(.+)",),
    "dispute_resolution": (r"(?:争议解决|争议处理)[:：]\s*(.+)",),
    "breach_liability": (r"(?:违约责任|违约条款)[:：]\s*(.+)",),
}

SECTION_PATTERNS: dict[str, tuple[str, ...]] = {
    "payment_terms": ("付款", "支付"),
    "warranty_period": ("质保", "保修"),
    "dispute_resolution": ("争议", "仲裁", "法院"),
    "breach_liability": ("违约", "责任"),
    "construction_period": ("工期", "期限"),
    "contract_amount": ("金额", "价款", "合同价"),
}


def _clean_value(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" ：:;；，,")


def normalize_review_text(raw_text: str) -> str:
    return unicodedata.normalize("NFKC", raw_text).translate(CHAR_NORMALIZATION_MAP)


def _extract_by_patterns(text: str, patterns: tuple[str, ...]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.MULTILINE)
        if match:
            value = _clean_value(match.group(1))
            if value:
                return value
    return None


def _extract_section(text: str, keywords: tuple[str, ...]) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if any(keyword in line for keyword in keywords):
            chunk = " ".join(lines[index : index + 3])
            return _clean_value(chunk)
    return None


def extract_contract_fields(raw_text: str) -> ContractExtractedFields:
    data: dict[str, str | None] = {}
    for field_name, patterns in FIELD_PATTERNS.items():
        value = _extract_by_patterns(raw_text, patterns)
        if value is None and field_name in SECTION_PATTERNS:
            value = _extract_section(raw_text, SECTION_PATTERNS[field_name])
        data[field_name] = value

    if data.get("contract_type") is None:
        if "施工合同" in raw_text:
            data["contract_type"] = "施工合同"
        elif "分包合同" in raw_text:
            data["contract_type"] = "分包合同"
        elif "采购合同" in raw_text:
            data["contract_type"] = "采购合同"

    return ContractExtractedFields(**data)


def identify_contract_risks(raw_text: str, fields: ContractExtractedFields) -> list[ReviewRiskItem]:
    risks: list[ReviewRiskItem] = []
    lowered_text = raw_text.replace(" ", "")

    for rule in BUILTIN_HEURISTIC_RULES:
        matched_keyword = next((kw for kw in rule.keywords if kw.replace(" ", "") in lowered_text), None)
        has_negative_keyword = any(kw.replace(" ", "") in lowered_text for kw in rule.negative_keywords)

        should_flag = False
        if matched_keyword:
            should_flag = True
        elif rule.code == "scope_unclear_risk" and not fields.project_name:
            should_flag = True
        elif rule.code == "missing_change_order_clause" and "变更" not in lowered_text and "签证" not in lowered_text:
            should_flag = True
        elif rule.code == "termination_clause_risk" and "解除" not in lowered_text:
            should_flag = True
        elif rule.code == "invoice_tax_risk" and "发票" not in lowered_text and "税" not in lowered_text:
            should_flag = True
        elif rule.code == "retention_money_risk" and fields.warranty_period and "质保金" not in lowered_text:
            should_flag = False

        if should_flag and not has_negative_keyword:
            risks.append(
                ReviewRiskItem(
                    code=rule.code,
                    title=rule.title,
                    level=rule.level,
                    matched_text=matched_keyword,
                    description=rule.description,
                    recommendation=rule.recommendation,
                    source="ai",
                    match_detail=ReviewMatchDetail(
                        condition_type="legacy_builtin",
                        condition_value=matched_keyword,
                        text_span=matched_keyword,
                    ),
                )
            )

    return risks


def merge_review_risks(rule_risks: list[ReviewRiskItem], ai_risks: list[ReviewRiskItem]) -> list[ReviewRiskItem]:
    merged: list[ReviewRiskItem] = []
    seen_keys: set[str] = set()

    def build_key(risk: ReviewRiskItem) -> str:
        return f"{risk.code}:{risk.title}".lower()

    for risk in rule_risks:
        key = build_key(risk)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        merged.append(risk)

    for risk in ai_risks:
        key = build_key(risk)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        merged.append(risk)

    return merged


def merge_review_providers(summary_provider: str, llm_risk_provider: str | None) -> str:
    if llm_risk_provider == "openai_compatible" and summary_provider == "openai_compatible":
        return "openai_compatible"
    if llm_risk_provider == "openai_compatible":
        return "mixed_rule_llm"
    return summary_provider


def log_llm_risk_supplement_result(
    db: Session,
    *,
    actor: User | None,
    contract_file_id: int,
    llm_risk_provider: str | None,
    llm_risk_count: int,
) -> None:
    if actor is None or llm_risk_provider is None:
        return

    if llm_risk_provider == "openai_compatible":
        create_review_log(
            db,
            operator_id=actor.id,
            target_type="contract",
            target_id=contract_file_id,
            action_type="llm_risk_supplement",
            action_detail=f"LLM supplemented {llm_risk_count} risk items",
        )
        return

    if llm_risk_provider == "mock_fallback":
        create_review_log(
            db,
            operator_id=actor.id,
            target_type="contract",
            target_id=contract_file_id,
            action_type="llm_risk_fallback",
            action_detail="LLM risk supplement failed or returned invalid output; skipped supplement",
        )


def _is_summary_degraded_from_provider(provider: str | None) -> bool:
    return (provider or "").strip() == "mock_fallback"


def _is_risk_degraded_from_provider(provider: str | None) -> bool:
    return (provider or "").strip() == "mock_fallback"


def log_llm_runtime_transition_events(
    db: Session,
    *,
    actor: User | None,
    contract_file_id: int,
    previous_version: ReviewVersion | None,
    current_summary_provider: str,
    current_risk_provider: str | None,
) -> None:
    if actor is None or previous_version is None:
        return

    previous_summary_degraded = _is_summary_degraded_from_provider(previous_version.summary_provider)
    current_summary_degraded = _is_summary_degraded_from_provider(current_summary_provider)
    if not previous_summary_degraded and current_summary_degraded:
        create_review_log(
            db,
            operator_id=actor.id,
            target_type="contract",
            target_id=contract_file_id,
            action_type="llm_summary_degraded",
            action_detail=(
                f"Summary chain degraded from {previous_version.summary_provider or '-'} "
                f"to {current_summary_provider or '-'}"
            ),
        )
    if previous_summary_degraded and not current_summary_degraded:
        create_review_log(
            db,
            operator_id=actor.id,
            target_type="contract",
            target_id=contract_file_id,
            action_type="llm_summary_recovered",
            action_detail=(
                f"Summary chain recovered from {previous_version.summary_provider or '-'} "
                f"to {current_summary_provider or '-'}"
            ),
        )

    previous_risk_degraded = _is_risk_degraded_from_provider(previous_version.risk_provider)
    current_risk_degraded = _is_risk_degraded_from_provider(current_risk_provider)
    if not previous_risk_degraded and current_risk_degraded:
        create_review_log(
            db,
            operator_id=actor.id,
            target_type="contract",
            target_id=contract_file_id,
            action_type="llm_risk_degraded",
            action_detail=(
                f"Risk supplement chain degraded from {previous_version.risk_provider or 'none'} "
                f"to {current_risk_provider or 'none'}"
            ),
        )
    if previous_risk_degraded and not current_risk_degraded:
        create_review_log(
            db,
            operator_id=actor.id,
            target_type="contract",
            target_id=contract_file_id,
            action_type="llm_risk_recovered",
            action_detail=(
                f"Risk supplement chain recovered from {previous_version.risk_provider or 'none'} "
                f"to {current_risk_provider or 'none'}"
            ),
        )


def generate_review_summary(
    db: Session,
    fields: ContractExtractedFields,
    risks: list[ReviewRiskItem],
) -> LlmSummaryRuntimeResult:
    return generate_review_summary_with_provider(db, fields, risks)


def review_contract_parse_result(
    db: Session,
    contract_file_id: int,
    actor: User | None = None,
    trigger_source: str = "manual",
) -> ContractReviewResponse:
    if actor is not None:
        ensure_can_modify_contracts(actor)

    contract_file = db.scalar(select(ContractFile).where(ContractFile.id == contract_file_id))
    if contract_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review failed: contract file not found.",
        )

    parse_result = db.scalar(
        select(ContractParseResult).where(ContractParseResult.contract_file_id == contract_file_id)
    )
    if parse_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review failed: parsed contract text not found.",
        )

    # If still processing but there's already some text, proceed with it
    if parse_result.parse_status == "processing":
        if not parse_result.raw_text.strip():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="合同正在后台解析中，暂无可审查文本，请稍后再试。",
            )
        # Text is available — proceed with review using current text
        parse_result.parse_status = "completed"
        parse_result.parse_mode = "text" if parse_result.parse_mode == "processing" else parse_result.parse_mode
        contract_file.status = "parsed"
        db.flush()

    if parse_result.parse_status == "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"合同解析失败，无法审查。{parse_result.parse_error or ''}".strip(),
        )

    if not parse_result.raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="合同文本为空，无法审查。请确认 PDF 文件是否可读取或等待 OCR 完成。",
        )

    normalized_text = normalize_review_text(parse_result.raw_text)
    logger.info("Reviewing contract %s, text length: %d chars", contract_file_id, len(normalized_text))

    try:
        logger.debug("Step 1: Extracting contract fields")
        fields = extract_contract_fields(normalized_text)
        logger.debug("Step 2: Evaluating review rules")
        rule_risks = evaluate_review_rules(db, normalized_text, fields)
        logger.debug("  Found %d rule risks", len(rule_risks))
        logger.debug("Step 3: Identifying AI risks")
        ai_risks = identify_contract_risks(normalized_text, fields)
        logger.debug("  Found %d AI risks", len(ai_risks))
        logger.debug("Step 4: Merging base risks")
        base_risks = merge_review_risks(rule_risks, ai_risks)
        logger.debug("  Total base risks: %d", len(base_risks))
        logger.debug("Step 5: Generating LLM risk supplements")
        llm_risk_result = generate_llm_risk_supplements(db, normalized_text, fields, base_risks)
        logger.debug("  LLM returned %d risks, provider=%s", len(llm_risk_result.risks), llm_risk_result.provider)
        risks = merge_review_risks(base_risks, llm_risk_result.risks)
        logger.debug("  Final risk count: %d", len(risks))
        logger.debug("Step 6: Generating review summary")
        summary_result = generate_review_summary(db, fields, risks)
        logger.debug("  Summary provider=%s, length=%d", summary_result.provider, len(summary_result.summary))
        provider = merge_review_providers(summary_result.provider, llm_risk_result.provider)
        logger.debug("  Final provider=%s", provider)
    except Exception as exc:
        db.rollback()
        logger.exception("Review processing failed at contract_file_id=%s", contract_file_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"审查处理失败：{type(exc).__name__}: {exc}",
        ) from exc
    log_llm_risk_supplement_result(
        db,
        actor=actor,
        contract_file_id=contract_file_id,
        llm_risk_provider=llm_risk_result.provider,
        llm_risk_count=len(llm_risk_result.risks),
    )
    existing_result = db.scalar(
        select(ContractReviewResult).where(ContractReviewResult.contract_file_id == contract_file_id)
    )
    previous_version = None
    if existing_result is not None and existing_result.latest_version_id is not None:
        previous_version = db.scalar(select(ReviewVersion).where(ReviewVersion.id == existing_result.latest_version_id))

    if existing_result is None:
        existing_result = ContractReviewResult(
            contract_file_id=contract_file_id,
            extracted_fields=fields.model_dump(),
            risks=[risk.model_dump() for risk in risks],
            summary=summary_result.summary,
            provider=provider,
        )
        db.add(existing_result)
    else:
        existing_result.extracted_fields = fields.model_dump()
        existing_result.risks = [risk.model_dump() for risk in risks]
        existing_result.summary = summary_result.summary
        existing_result.provider = provider

    version = create_review_version(
        db,
        contract_id=contract_file_id,
        triggered_by=actor.id if actor is not None else None,
        trigger_source=trigger_source,
        extracted_fields=fields,
        risks=risks,
        summary=summary_result.summary,
        provider=provider,
        summary_provider=summary_result.provider,
        summary_success=summary_result.success,
        summary_message=summary_result.message,
        risk_provider=llm_risk_result.provider,
        risk_success=llm_risk_result.success,
        risk_message=llm_risk_result.message,
    )
    log_llm_runtime_transition_events(
        db,
        actor=actor,
        contract_file_id=contract_file_id,
        previous_version=previous_version,
        current_summary_provider=summary_result.provider,
        current_risk_provider=llm_risk_result.provider,
    )
    try:
        existing_result.latest_version_id = version.id
        existing_result.latest_version_no = version.version_no
        contract_file.status = "reviewed" if contract_file.status != "archived" else contract_file.status
        if actor is not None:
            create_review_log(
                db,
                operator_id=actor.id,
                target_type="contract",
                target_id=contract_file_id,
                action_type="review_contract",
                action_detail=f"Triggered review version {version.version_no} via {trigger_source}",
            )

        db.commit()
        db.refresh(existing_result)
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to save review result for contract_file_id=%s", contract_file_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存审查结果失败：{type(exc).__name__}: {exc}",
        ) from exc

    return ContractReviewResponse(
        contract_file_id=contract_file_id,
        review_result_id=existing_result.id,
        provider=existing_result.provider,
        extracted_fields=fields,
        risks=risks,
        summary=summary_result.summary,
    )
