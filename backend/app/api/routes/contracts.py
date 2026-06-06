from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from urllib.parse import quote

from app.api.deps import get_db, require_contract_read_access, require_contract_write_access
from app.models.user import User
from app.schemas.contract import (
    ContractDetailResponse,
    ContractListItem,
    ContractListQuery,
    ContractMetadataUpdateRequest,
    ContractUploadResponse,
)
from app.schemas.review import ContractReviewResponse
from app.services.contract_service import (
    build_pending_parse_content,
    extract_pdf_text,
    get_contract_detail,
    get_contract_list,
    inspect_pdf_text_layer,
    read_pdf_upload,
    run_background_ocr_parse,
    save_contract_and_parse_result,
    should_use_async_ocr,
    update_contract_metadata,
)
from app.services.contract_review_service import review_contract_parse_result
from app.services.report_service import generate_contract_review_report

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.get("", response_model=list[ContractListItem])
def list_contracts(
    contract_name: Optional[str] = Query(default=None),
    project_name: Optional[str] = Query(default=None),
    owner_id: Optional[int] = Query(default=None),
    status_value: Optional[str] = Query(default=None, alias="status"),
    category: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    risk_level: Optional[str] = Query(default=None),
    created_from: Optional[str] = Query(default=None),
    created_to: Optional[str] = Query(default=None),
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_contract_read_access),
) -> list[ContractListItem]:
    return get_contract_list(
        db,
        current_user,
        ContractListQuery(
            contract_name=contract_name,
            project_name=project_name,
            owner_id=owner_id,
            status=status_value,
            category=category,
            tag=tag,
            risk_level=risk_level,
            created_from=created_from,
            created_to=created_to,
            include_archived=include_archived,
        ),
    )


@router.get("/{contract_file_id}", response_model=ContractDetailResponse)
def get_contract(
    contract_file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_contract_read_access),
) -> ContractDetailResponse:
    return get_contract_detail(db, contract_file_id, current_user)


@router.post(
    "/upload",
    response_model=ContractUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_contract(
    background_tasks: BackgroundTasks,
    version_of_contract_id: Optional[int] = Query(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_contract_write_access),
) -> ContractUploadResponse:
    file_bytes = await read_pdf_upload(file)
    candidate = inspect_pdf_text_layer(file_bytes)
    parsed_content = (
        build_pending_parse_content(candidate)
        if should_use_async_ocr(candidate)
        else extract_pdf_text(file_bytes)
    )
    contract_file, parse_result = save_contract_and_parse_result(
        db,
        original_filename=file.filename or "unknown.pdf",
        content_type=file.content_type or "application/pdf",
        file_bytes=file_bytes,
        parsed_content=parsed_content,
        actor=current_user,
        version_of_contract_id=version_of_contract_id,
    )
    if parse_result.parse_status == "processing":
        background_tasks.add_task(run_background_ocr_parse, contract_file.id)

    return ContractUploadResponse(
        file_id=contract_file.id,
        contract_group_id=contract_file.version_root_id or contract_file.id,
        upload_version_no=contract_file.upload_version_no,
        parse_result_id=parse_result.id,
        original_filename=contract_file.original_filename,
        stored_filename=contract_file.stored_filename,
        file_size=contract_file.file_size,
        page_count=parse_result.page_count,
        parse_status=parse_result.parse_status,
        parse_mode=parse_result.parse_mode,
        parse_notice=parse_result.parse_notice,
        parse_error=parse_result.parse_error,
        raw_text_preview=parse_result.raw_text[:500],
    )


@router.post(
    "/{contract_file_id}/review",
    response_model=ContractReviewResponse,
)
def review_contract(
    contract_file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_contract_write_access),
) -> ContractReviewResponse:
    return review_contract_parse_result(db, contract_file_id, current_user, trigger_source="manual")


@router.get("/{contract_file_id}/report")
def export_review_report(
    contract_file_id: int,
    version_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_contract_read_access),
) -> StreamingResponse:
    filename, pdf_bytes, _ = generate_contract_review_report(db, contract_file_id, current_user, version_id)
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.patch("/{contract_file_id}", response_model=ContractDetailResponse)
def update_contract(
    contract_file_id: int,
    payload: ContractMetadataUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_contract_write_access),
) -> ContractDetailResponse:
    return update_contract_metadata(db, contract_file_id, payload, current_user)
