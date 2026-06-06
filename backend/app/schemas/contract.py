from typing import Optional

from pydantic import BaseModel, Field


class ContractUploadResponse(BaseModel):
    file_id: int
    contract_group_id: int
    upload_version_no: int
    parse_result_id: int
    original_filename: str
    stored_filename: str
    file_size: int
    page_count: int
    parse_status: str
    parse_mode: str
    parse_notice: Optional[str] = None
    parse_error: Optional[str] = None
    raw_text_preview: str


class ContractListItem(BaseModel):
    file_id: int
    contract_group_id: int
    upload_version_no: int
    original_filename: str
    contract_name: Optional[str] = None
    project_name: Optional[str] = None
    stored_filename: str
    file_size: int
    owner_id: Optional[int] = None
    owner_username: Optional[str] = None
    category: Optional[str] = None
    tags: list[str]
    status: str
    archived_at: Optional[str] = None
    created_at: str
    page_count: int
    parse_status: str
    parse_mode: str
    review_status: str
    risk_levels: list[str]
    summary: Optional[str] = None


class ContractDetailResponse(BaseModel):
    file_id: int
    contract_group_id: int
    upload_version_no: int
    version_count: int
    original_filename: str
    contract_name: Optional[str] = None
    project_name: Optional[str] = None
    stored_filename: str
    file_path: str
    content_type: str
    file_size: int
    owner_id: Optional[int] = None
    owner_username: Optional[str] = None
    category: Optional[str] = None
    tags: list[str]
    status: str
    archived_at: Optional[str] = None
    updated_by: Optional[int] = None
    created_at: str
    updated_at: str
    page_count: int
    parse_status: str
    parse_mode: str
    parse_notice: Optional[str] = None
    parse_error: Optional[str] = None
    raw_text: str
    review_status: str
    latest_version_id: Optional[int] = None
    latest_version_no: Optional[int] = None
    review_result: Optional[dict] = None


class ContractListQuery(BaseModel):
    contract_name: Optional[str] = None
    project_name: Optional[str] = None
    owner_id: Optional[int] = None
    status: Optional[str] = None
    category: Optional[str] = None
    tag: Optional[str] = None
    risk_level: Optional[str] = None
    created_from: Optional[str] = None
    created_to: Optional[str] = None
    include_archived: bool = False


class ContractMetadataUpdateRequest(BaseModel):
    original_filename: Optional[str] = Field(default=None, min_length=1, max_length=255)
    owner_id: Optional[int] = None
    category: Optional[str] = Field(default=None, max_length=100)
    tags: Optional[list[str]] = None
    status: Optional[str] = Field(default=None, pattern="^(uploaded|parsed|reviewed|archived)$")
    archived: Optional[bool] = None
