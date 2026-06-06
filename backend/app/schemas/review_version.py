from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ReviewVersionItem(BaseModel):
    id: int
    contract_id: int
    version_no: int
    file_id: int
    original_filename: str
    latest_review_version_no: Optional[int] = None
    triggered_by: Optional[int] = None
    triggered_by_username: Optional[str] = None
    trigger_source: str
    summary: str
    provider: str
    summary_provider: Optional[str] = None
    summary_success: Optional[bool] = None
    risk_provider: Optional[str] = None
    risk_success: Optional[bool] = None
    overall_risk_level: str
    risk_count: int
    created_at: str


class ReviewVersionDetail(BaseModel):
    id: int
    contract_id: int
    version_no: int
    file_id: int
    original_filename: str
    review_status: str
    triggered_by: Optional[int] = None
    triggered_by_username: Optional[str] = None
    trigger_source: str
    extracted_fields: dict
    risk_items: list
    summary: str
    provider: str
    summary_provider: Optional[str] = None
    summary_success: Optional[bool] = None
    summary_message: Optional[str] = None
    risk_provider: Optional[str] = None
    risk_success: Optional[bool] = None
    risk_message: Optional[str] = None
    overall_risk_level: str
    created_at: str


class ReviewVersionFieldChange(BaseModel):
    field: str
    label: str
    before_value: str
    after_value: str


class ReviewVersionRiskSnapshot(BaseModel):
    code: str
    title: str
    level: str
    source: Optional[str] = None


class ReviewVersionRiskLevelChange(BaseModel):
    code: str
    title: str
    before_level: str
    after_level: str
    source: Optional[str] = None


class ReviewVersionRuntimeChange(BaseModel):
    label: str
    before_value: str
    after_value: str


class ReviewVersionCompareResponse(BaseModel):
    contract_id: int
    base_version_id: int
    base_version_no: int
    target_version_id: int
    target_version_no: int
    summary_changed: bool
    runtime_changed: bool
    summary_degraded: bool
    risk_degraded: bool
    degradation_events: list[str]
    summary_recovered: bool
    risk_recovered: bool
    recovery_events: list[str]
    runtime_changes: list[ReviewVersionRuntimeChange]
    field_changes: list[ReviewVersionFieldChange]
    added_risks: list[ReviewVersionRiskSnapshot]
    removed_risks: list[ReviewVersionRiskSnapshot]
    level_changed_risks: list[ReviewVersionRiskLevelChange]
