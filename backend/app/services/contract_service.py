from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings, settings_upload_path
from app.db.session import SessionLocal
from app.models.contract_file import ContractFile
from app.models.contract_parse_result import ContractParseResult
from app.models.contract_review_result import ContractReviewResult
from app.models.user import User
from app.schemas.contract import ContractDetailResponse, ContractListItem, ContractListQuery, ContractMetadataUpdateRequest
from app.services.permission_service import ensure_can_modify_contracts, ensure_can_view_contracts
from app.services.contract_review_service import review_contract_parse_result
from app.services.ocr_service import OcrDependencyError, ensure_ocr_dependencies, extract_text_with_ocr
from app.services.review_log_service import create_review_log

PDF_MAGIC_HEADER = b"%PDF"
MIN_DIRECT_TEXT_LENGTH = 80
ALLOWED_CONTRACT_STATUSES = {"uploaded", "parsed", "reviewed", "archived"}


@dataclass
class ParsedPdfContent:
    raw_text: str
    page_count: int
    parse_status: str
    parse_mode: str
    parse_notice: str | None = None
    parse_error: str | None = None


@dataclass
class ParsedPdfCandidate:
    raw_text: str
    page_count: int


def ensure_upload_dir() -> None:
    settings_upload_path.mkdir(parents=True, exist_ok=True)


async def read_pdf_upload(upload: UploadFile) -> bytes:
    if not upload.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload failed: missing filename.",
        )

    if not upload.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload failed: only PDF files are allowed.",
        )

    if upload.content_type not in {"application/pdf", "application/x-pdf"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload failed: invalid content type, expected application/pdf.",
        )

    file_bytes = await upload.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload failed: file is empty.",
        )

    if not file_bytes.startswith(PDF_MAGIC_HEADER):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload failed: file content is not a valid PDF.",
        )

    return file_bytes


def inspect_pdf_text_layer(file_bytes: bytes) -> ParsedPdfCandidate:
    try:
        reader = PdfReader(BytesIO(file_bytes))
    except PdfReadError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload failed: unable to read PDF content. {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload failed: PDF parsing failed. {exc}",
        ) from exc

    page_texts = [(page.extract_text() or "").strip() for page in reader.pages]
    page_count = len(reader.pages)
    raw_text = "\n".join(text for text in page_texts if text).strip()
    return ParsedPdfCandidate(raw_text=raw_text, page_count=page_count)


def extract_pdf_text(file_bytes: bytes) -> ParsedPdfContent:
    candidate = inspect_pdf_text_layer(file_bytes)
    if _looks_like_extractable_text(candidate.raw_text, candidate.page_count):
        return ParsedPdfContent(
            raw_text=candidate.raw_text,
            page_count=candidate.page_count,
            parse_status="completed",
            parse_mode="text",
        )

    return _extract_with_ocr(file_bytes, candidate)


def should_use_async_ocr(candidate: ParsedPdfCandidate) -> bool:
    # Only use async OCR if there's genuinely no extractable text at all
    # For large documents with some text, prefer immediate processing
    return candidate.page_count >= settings.async_ocr_page_threshold and not _looks_like_extractable_text(
        candidate.raw_text,
        candidate.page_count,
    ) and not candidate.raw_text.strip()


def build_pending_parse_content(candidate: ParsedPdfCandidate) -> ParsedPdfContent:
    try:
        ensure_ocr_dependencies()
    except OcrDependencyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Upload failed: no extractable text found in the PDF and OCR fallback is unavailable. "
                f"{exc}"
            ),
        ) from exc

    parse_mode = "ocr" if not candidate.raw_text else "hybrid"
    return ParsedPdfContent(
        raw_text="",
        page_count=candidate.page_count,
        parse_status="processing",
        parse_mode=parse_mode,
        parse_notice=(
            "The PDF looks like a scanned document. OCR has been queued in the background; "
            "refresh this page in a moment."
        ),
    )


def _extract_with_ocr(file_bytes: bytes, candidate: ParsedPdfCandidate) -> ParsedPdfContent:
    try:
        ocr_result = extract_text_with_ocr(file_bytes)
    except OcrDependencyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Upload failed: no extractable text found in the PDF and OCR fallback is unavailable. "
                f"{exc}"
            ),
        ) from exc

    return ParsedPdfContent(
        raw_text=ocr_result.raw_text,
        page_count=ocr_result.page_count,
        parse_status="completed",
        parse_mode="ocr" if not candidate.raw_text else "hybrid",
        parse_notice="The PDF had little or no embedded text. OCR fallback was used to recognize scanned pages.",
    )


def _looks_like_extractable_text(raw_text: str, page_count: int) -> bool:
    effective_chars = sum(1 for char in raw_text if not char.isspace())
    if effective_chars == 0:
        return False

    if effective_chars >= MIN_DIRECT_TEXT_LENGTH:
        return True

    average_chars_per_page = effective_chars / max(page_count, 1)
    return average_chars_per_page >= 40


def save_contract_and_parse_result(
    db: Session,
    *,
    original_filename: str,
    content_type: str,
    file_bytes: bytes,
    parsed_content: ParsedPdfContent,
    actor: User,
    version_of_contract_id: int | None = None,
) -> tuple[ContractFile, ContractParseResult]:
    ensure_can_modify_contracts(actor)
    ensure_upload_dir()

    stored_filename = f"{uuid4().hex}.pdf"
    file_path = settings_upload_path / stored_filename
    base_contract: ContractFile | None = None
    version_root_id: int | None = None
    upload_version_no = 1

    if version_of_contract_id is not None:
        base_contract = db.scalar(select(ContractFile).where(ContractFile.id == version_of_contract_id))
        if base_contract is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Base contract version not found.")
        version_root_id = resolve_contract_group_id(base_contract)
        current_max_version = db.scalar(
            select(func.max(ContractFile.upload_version_no)).where(ContractFile.version_root_id == version_root_id)
        )
        upload_version_no = (current_max_version or 0) + 1

    try:
        file_path.write_bytes(file_bytes)

        contract_file = ContractFile(
            version_root_id=version_root_id,
            upload_version_no=upload_version_no,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=str(file_path),
            content_type=content_type,
            file_size=len(file_bytes),
            owner_id=base_contract.owner_id if base_contract is not None else actor.id,
            category=base_contract.category if base_contract is not None else None,
            tags=list(base_contract.tags or []) if base_contract is not None else [],
            status="uploaded" if parsed_content.parse_status == "processing" else "parsed",
            updated_by=actor.id,
        )
        db.add(contract_file)
        db.flush()
        if contract_file.version_root_id is None:
            contract_file.version_root_id = contract_file.id
            db.flush()

        parse_result = ContractParseResult(
            contract_file_id=contract_file.id,
            page_count=parsed_content.page_count,
            parse_status=parsed_content.parse_status,
            parse_mode=parsed_content.parse_mode,
            parse_notice=parsed_content.parse_notice,
            parse_error=parsed_content.parse_error,
            raw_text=parsed_content.raw_text,
        )
        db.add(parse_result)
        create_review_log(
            db,
            operator_id=actor.id,
            target_type="contract",
            target_id=contract_file.id,
            action_type="upload_contract",
            action_detail=(
                f"Uploaded {original_filename}"
                if version_of_contract_id is None
                else f"Uploaded {original_filename} as version V{contract_file.upload_version_no}"
            ),
        )
        db.commit()
        db.refresh(contract_file)
        db.refresh(parse_result)
        return contract_file, parse_result
    except HTTPException:
        if file_path.exists():
            file_path.unlink()
        db.rollback()
        raise
    except Exception as exc:
        if file_path.exists():
            file_path.unlink()
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: unable to save file metadata or parsed text. {exc}",
        ) from exc


def run_background_ocr_parse(contract_file_id: int) -> None:
    db = SessionLocal()
    try:
        contract_file = db.scalar(select(ContractFile).where(ContractFile.id == contract_file_id))
        parse_result = db.scalar(
            select(ContractParseResult).where(ContractParseResult.contract_file_id == contract_file_id)
        )
        if contract_file is None or parse_result is None:
            return

        file_bytes = settings_upload_path.joinpath(contract_file.stored_filename).read_bytes()
        candidate = inspect_pdf_text_layer(file_bytes)
        parsed_content = _extract_with_ocr(file_bytes, candidate)

        parse_result.page_count = parsed_content.page_count
        parse_result.parse_status = parsed_content.parse_status
        parse_result.parse_mode = parsed_content.parse_mode
        parse_result.parse_notice = parsed_content.parse_notice
        parse_result.parse_error = None
        parse_result.raw_text = parsed_content.raw_text
        contract_file.status = "parsed"
        db.commit()

        try:
            review_contract_parse_result(db, contract_file_id, trigger_source="auto_after_ocr")
        except Exception as exc:
            refreshed_parse_result = db.scalar(
                select(ContractParseResult).where(ContractParseResult.contract_file_id == contract_file_id)
            )
            if refreshed_parse_result is not None:
                refreshed_parse_result.parse_notice = (
                    f"{parsed_content.parse_notice} Automatic review failed: {exc}"
                )
                db.commit()
    except Exception as exc:
        db.rollback()
        parse_result = db.scalar(
            select(ContractParseResult).where(ContractParseResult.contract_file_id == contract_file_id)
        )
        if parse_result is not None:
            parse_result.parse_status = "failed"
            parse_result.parse_error = str(exc)
            parse_result.parse_notice = "Background OCR failed. Check OCR dependencies or scan quality."
            parse_result.raw_text = ""
            db.commit()
    finally:
        db.close()


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid datetime format: {value}",
        ) from exc


def _normalize_tags(tags: list[str] | None) -> list[str]:
    if tags is None:
        return []
    normalized = []
    seen: set[str] = set()
    for tag in tags:
        cleaned = tag.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized


def _build_contract_list_item(
    contract_file: ContractFile,
    parse_result: ContractParseResult | None,
    review_result: ContractReviewResult | None,
) -> ContractListItem:
    extracted_fields = review_result.extracted_fields if review_result else {}
    risks = review_result.risks if review_result else []
    risk_levels = sorted({risk.get("level", "unknown") for risk in risks})
    return ContractListItem(
        file_id=contract_file.id,
        contract_group_id=resolve_contract_group_id(contract_file),
        upload_version_no=contract_file.upload_version_no,
        original_filename=contract_file.original_filename,
        contract_name=extracted_fields.get("contract_name"),
        project_name=extracted_fields.get("project_name"),
        stored_filename=contract_file.stored_filename,
        file_size=contract_file.file_size,
        owner_id=contract_file.owner_id,
        owner_username=contract_file.owner.username if contract_file.owner else None,
        category=contract_file.category,
        tags=contract_file.tags or [],
        status=contract_file.status,
        archived_at=contract_file.archived_at.isoformat() if contract_file.archived_at else None,
        created_at=contract_file.created_at.isoformat(),
        page_count=parse_result.page_count if parse_result else 0,
        parse_status=parse_result.parse_status if parse_result else "missing",
        parse_mode=parse_result.parse_mode if parse_result else "unknown",
        review_status="completed" if review_result else "pending",
        risk_levels=risk_levels,
        summary=review_result.summary if review_result else None,
    )


def _matches_query(
    item: ContractListItem,
    query: ContractListQuery,
    created_at: datetime,
) -> bool:
    contract_name = (item.contract_name or "").lower()
    project_name = (item.project_name or "").lower()
    filename = (item.original_filename or "").lower()
    if query.contract_name and query.contract_name.lower() not in contract_name and query.contract_name.lower() not in filename:
        return False
    if query.project_name and query.project_name.lower() not in project_name:
        return False
    if query.owner_id is not None and item.owner_id != query.owner_id:
        return False
    if query.status and item.status != query.status:
        return False
    if query.category and item.category != query.category:
        return False
    if query.tag and query.tag not in item.tags:
        return False
    if query.risk_level and query.risk_level not in item.risk_levels:
        return False
    if not query.include_archived and item.status == "archived":
        return False
    created_from = _parse_datetime(query.created_from)
    created_to = _parse_datetime(query.created_to)
    if created_from and created_at < created_from:
        return False
    if created_to and created_at > created_to:
        return False
    return True


def get_contract_list(db: Session, actor: User, query: ContractListQuery) -> list[ContractListItem]:
    ensure_can_view_contracts(actor)
    contract_files = db.scalars(
        select(ContractFile)
        .options(
            joinedload(ContractFile.owner),
            joinedload(ContractFile.parse_result),
        )
        .order_by(ContractFile.created_at.desc(), ContractFile.id.desc())
    ).all()

    items: list[ContractListItem] = []
    for contract_file in contract_files:
        parse_result = contract_file.parse_result
        review_result = db.scalar(
            select(ContractReviewResult).where(ContractReviewResult.contract_file_id == contract_file.id)
        )
        item = _build_contract_list_item(contract_file, parse_result, review_result)
        if _matches_query(item, query, contract_file.created_at):
            items.append(item)

    return items


def get_contract_detail(db: Session, contract_file_id: int, actor: User) -> ContractDetailResponse:
    ensure_can_view_contracts(actor)
    contract_file = db.scalar(
        select(ContractFile)
        .options(joinedload(ContractFile.owner))
        .where(ContractFile.id == contract_file_id)
    )
    if contract_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found.",
        )

    parse_result = db.scalar(
        select(ContractParseResult).where(ContractParseResult.contract_file_id == contract_file_id)
    )
    if parse_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract parse result not found.",
        )

    review_result = db.scalar(
        select(ContractReviewResult).where(ContractReviewResult.contract_file_id == contract_file_id)
    )

    version_count = db.scalar(
        select(func.count())
        .select_from(ContractFile)
        .where(ContractFile.version_root_id == resolve_contract_group_id(contract_file))
    ) or 1

    return ContractDetailResponse(
        file_id=contract_file.id,
        contract_group_id=resolve_contract_group_id(contract_file),
        upload_version_no=contract_file.upload_version_no,
        version_count=version_count,
        original_filename=contract_file.original_filename,
        contract_name=review_result.extracted_fields.get("contract_name") if review_result else None,
        project_name=review_result.extracted_fields.get("project_name") if review_result else None,
        stored_filename=contract_file.stored_filename,
        file_path=contract_file.file_path,
        content_type=contract_file.content_type,
        file_size=contract_file.file_size,
        owner_id=contract_file.owner_id,
        owner_username=contract_file.owner.username if contract_file.owner else None,
        category=contract_file.category,
        tags=contract_file.tags or [],
        status=contract_file.status,
        archived_at=contract_file.archived_at.isoformat() if contract_file.archived_at else None,
        updated_by=contract_file.updated_by,
        created_at=contract_file.created_at.isoformat(),
        updated_at=contract_file.updated_at.isoformat(),
        page_count=parse_result.page_count,
        parse_status=parse_result.parse_status,
        parse_mode=parse_result.parse_mode,
        parse_notice=parse_result.parse_notice,
        parse_error=parse_result.parse_error,
        raw_text=parse_result.raw_text,
        review_status="completed" if review_result else "pending",
        latest_version_id=review_result.latest_version_id if review_result else None,
        latest_version_no=review_result.latest_version_no if review_result else None,
        review_result={
            "review_result_id": review_result.id,
            "latest_version_id": review_result.latest_version_id,
            "latest_version_no": review_result.latest_version_no,
            "provider": review_result.provider,
            "extracted_fields": review_result.extracted_fields,
            "risks": review_result.risks,
            "summary": review_result.summary,
            "created_at": review_result.created_at.isoformat(),
        }
        if review_result
        else None,
    )


def update_contract_metadata(
    db: Session,
    contract_file_id: int,
    payload: ContractMetadataUpdateRequest,
    actor: User,
) -> ContractDetailResponse:
    ensure_can_modify_contracts(actor)
    contract_file = db.scalar(select(ContractFile).where(ContractFile.id == contract_file_id))
    if contract_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found.")

    if payload.owner_id is not None:
        owner = db.scalar(select(User).where(User.id == payload.owner_id))
        if owner is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner user not found.")
        contract_file.owner_id = owner.id

    if payload.original_filename is not None:
        contract_file.original_filename = payload.original_filename.strip()
    if payload.category is not None:
        contract_file.category = payload.category.strip() or None
    if payload.tags is not None:
        contract_file.tags = _normalize_tags(payload.tags)

    if payload.status is not None:
        if payload.status not in ALLOWED_CONTRACT_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported contract status.")
        contract_file.status = payload.status
        if payload.status == "archived":
            contract_file.archived_at = datetime.now(timezone.utc)
        elif contract_file.archived_at is not None:
            contract_file.archived_at = None

    if payload.archived is not None:
        if payload.archived:
            contract_file.status = "archived"
            contract_file.archived_at = datetime.now(timezone.utc)
        else:
            if contract_file.status == "archived":
                review_result = db.scalar(
                    select(ContractReviewResult).where(ContractReviewResult.contract_file_id == contract_file.id)
                )
                parse_result = db.scalar(
                    select(ContractParseResult).where(ContractParseResult.contract_file_id == contract_file.id)
                )
                contract_file.status = _derive_contract_status(parse_result, review_result)
            contract_file.archived_at = None

    contract_file.updated_by = actor.id
    create_review_log(
        db,
        operator_id=actor.id,
        target_type="contract",
        target_id=contract_file_id,
        action_type="edit_contract",
        action_detail="Updated contract metadata",
    )
    db.commit()
    return get_contract_detail(db, contract_file_id, actor)


def _derive_contract_status(
    parse_result: ContractParseResult | None,
    review_result: ContractReviewResult | None,
) -> str:
    if review_result is not None:
        return "reviewed"
    if parse_result is None:
        return "uploaded"
    if parse_result.parse_status == "completed":
        return "parsed"
    return "uploaded"


def resolve_contract_group_id(contract_file: ContractFile) -> int:
    return contract_file.version_root_id or contract_file.id
