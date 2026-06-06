from typing import List, Optional

from pydantic import BaseModel


class ReviewMatchDetail(BaseModel):
    condition_type: Optional[str] = None
    condition_value: Optional[str] = None
    priority: Optional[int] = None
    text_span: Optional[str] = None


class ReviewRiskItem(BaseModel):
    code: str
    title: str
    level: str
    matched_text: Optional[str] = None
    description: str
    recommendation: str
    source: str = "ai"
    rule_id: Optional[int] = None
    match_detail: Optional[ReviewMatchDetail] = None


class ContractExtractedFields(BaseModel):
    contract_name: Optional[str] = None
    contract_number: Optional[str] = None
    project_name: Optional[str] = None
    party_a: Optional[str] = None
    party_b: Optional[str] = None
    contract_type: Optional[str] = None
    sign_date: Optional[str] = None
    contract_amount: Optional[str] = None
    construction_period: Optional[str] = None
    payment_terms: Optional[str] = None
    warranty_period: Optional[str] = None
    dispute_resolution: Optional[str] = None
    breach_liability: Optional[str] = None


class ContractReviewResponse(BaseModel):
    contract_file_id: int
    review_result_id: int
    provider: str
    extracted_fields: ContractExtractedFields
    risks: List[ReviewRiskItem]
    summary: str
