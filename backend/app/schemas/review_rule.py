from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ReviewRuleBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    rule_code: str = Field(min_length=1, max_length=64)
    risk_type: str = Field(min_length=1, max_length=100)
    condition_type: str = Field(pattern="^(keyword|regex|contains_any|contains_all)$")
    condition_value: str = Field(min_length=1)
    risk_level: str = Field(pattern="^(high|medium|low)$")
    suggestion: str = Field(min_length=1)
    priority: int = Field(default=100, ge=0, le=100000)
    is_active: bool = True
    contract_type_scope: Optional[str] = None


class ReviewRuleCreateRequest(ReviewRuleBase):
    pass


class ReviewRuleUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    risk_type: Optional[str] = Field(default=None, min_length=1, max_length=100)
    condition_type: Optional[str] = Field(default=None, pattern="^(keyword|regex|contains_any|contains_all)$")
    condition_value: Optional[str] = Field(default=None, min_length=1)
    risk_level: Optional[str] = Field(default=None, pattern="^(high|medium|low)$")
    suggestion: Optional[str] = Field(default=None, min_length=1)
    priority: Optional[int] = Field(default=None, ge=0, le=100000)
    is_active: Optional[bool] = None
    contract_type_scope: Optional[str] = None
    is_deleted: Optional[bool] = None


class ReviewRuleResponse(BaseModel):
    id: int
    name: str
    rule_code: str
    risk_type: str
    condition_type: str
    condition_value: str
    risk_level: str
    suggestion: str
    priority: int
    is_active: bool
    is_deleted: bool
    contract_type_scope: Optional[str] = None
    created_by: Optional[int] = None
    created_at: str
    updated_at: str
