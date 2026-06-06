from __future__ import annotations

from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.review_version import ReviewVersion
from app.models.user import User
from app.services.contract_review_service import review_contract_parse_result
from app.services.contract_service import get_contract_detail
from app.services.permission_service import ensure_can_view_contracts
from app.services.review_log_service import create_review_log

pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))


def _build_styles() -> dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "TitleZh",
            parent=styles["Title"],
            fontName="STSong-Light",
            fontSize=18,
            leading=24,
            textColor=colors.HexColor("#223043"),
        ),
        "heading": ParagraphStyle(
            "HeadingZh",
            parent=styles["Heading2"],
            fontName="STSong-Light",
            fontSize=13,
            leading=18,
            textColor=colors.HexColor("#223043"),
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "BodyZh",
            parent=styles["BodyText"],
            fontName="STSong-Light",
            fontSize=10.5,
            leading=16,
            textColor=colors.HexColor("#334155"),
        ),
    }


def _table_data_from_fields(extracted_fields: dict) -> list[list[str]]:
    label_map = [
        ("合同名称", extracted_fields.get("contract_name") or "-"),
        ("合同编号", extracted_fields.get("contract_number") or "-"),
        ("项目名称", extracted_fields.get("project_name") or "-"),
        ("甲方", extracted_fields.get("party_a") or "-"),
        ("乙方", extracted_fields.get("party_b") or "-"),
        ("合同类型", extracted_fields.get("contract_type") or "-"),
        ("签订日期", extracted_fields.get("sign_date") or "-"),
        ("合同金额", extracted_fields.get("contract_amount") or "-"),
        ("工期", extracted_fields.get("construction_period") or "-"),
        ("付款条款", extracted_fields.get("payment_terms") or "-"),
        ("质保期", extracted_fields.get("warranty_period") or "-"),
        ("争议解决", extracted_fields.get("dispute_resolution") or "-"),
        ("违约责任", extracted_fields.get("breach_liability") or "-"),
    ]
    return [["字段", "内容"], *label_map]


def generate_contract_review_report(
    db: Session,
    contract_file_id: int,
    actor: User,
    version_id: int | None = None,
) -> tuple[str, bytes, int | None]:
    ensure_can_view_contracts(actor)
    detail = get_contract_detail(db, contract_file_id, actor)
    if detail.review_result is None:
        review_contract_parse_result(db, contract_file_id, actor, trigger_source="manual")
        detail = get_contract_detail(db, contract_file_id, actor)

    if detail.review_result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Export failed: review result is not available.",
        )

    report_version_id = detail.latest_version_id
    extracted_fields = detail.review_result["extracted_fields"]
    risks = detail.review_result["risks"]
    summary = detail.review_result["summary"]
    version_no = detail.latest_version_no
    if version_id is not None:
        version = db.scalar(
            select(ReviewVersion).where(
                ReviewVersion.contract_id == contract_file_id,
                ReviewVersion.id == version_id,
            )
        )
        if version is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review version not found.")
        report_version_id = version.id
        extracted_fields = version.extracted_fields
        risks = version.risk_items
        summary = version.summary
        version_no = version.version_no

    styles = _build_styles()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )

    story = [
        Paragraph(settings.report_title, styles["title"]),
        Spacer(1, 10),
        Paragraph(f"文件名：{detail.original_filename}", styles["body"]),
        Paragraph(f"文件 ID：{detail.file_id}", styles["body"]),
        Paragraph(f"审查状态：{detail.review_status}", styles["body"]),
        Paragraph(f"审查版本：{version_no or '-'}", styles["body"]),
        Spacer(1, 12),
        Paragraph("一、合同基础信息", styles["heading"]),
    ]

    field_table = Table(_table_data_from_fields(extracted_fields), colWidths=[36 * mm, 140 * mm])
    field_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF1FB")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#223043")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEADING", (0, 0), (-1, -1), 14),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ]
        )
    )
    story.extend([field_table, Spacer(1, 12)])

    story.append(Paragraph("二、风险识别结果", styles["heading"]))
    if risks:
        for index, risk in enumerate(risks, start=1):
            story.append(
                Paragraph(
                    f"{index}. {risk['title']}（{risk['level']}）<br/>"
                    f"说明：{risk['description']}<br/>"
                    f"命中内容：{risk.get('matched_text') or '规则缺失或兜底命中'}<br/>"
                    f"建议：{risk['recommendation']}",
                    styles["body"],
                )
            )
            story.append(Spacer(1, 8))
    else:
        story.append(Paragraph("未识别到明显风险。", styles["body"]))
        story.append(Spacer(1, 8))

    story.append(Paragraph("三、审查摘要", styles["heading"]))
    story.append(Paragraph(summary, styles["body"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("四、原始解析文本（节选）", styles["heading"]))
    story.append(Paragraph((detail.raw_text[:2500] or "-").replace("\n", "<br/>"), styles["body"]))

    document.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    filename = f"{Path(detail.original_filename).stem}-审查报告.pdf"
    create_review_log(
        db,
        operator_id=actor.id,
        target_type="contract",
        target_id=contract_file_id,
        action_type="export_report",
        action_detail=f"Exported report for version {report_version_id or 'latest'}",
    )
    db.commit()
    return filename, pdf_bytes, report_version_id
