from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SystemSettingsResponse(BaseModel):
    review_provider: str
    llm_base_url: str
    llm_model: str
    llm_timeout_seconds: int
    llm_api_key_configured: bool
    effective_provider: str
    llm_ready: bool
    status_message: str
    last_test_success: Optional[bool] = None
    last_test_message: Optional[str] = None
    last_tested_at: Optional[str] = None
    last_summary_call_success: Optional[bool] = None
    last_summary_call_message: Optional[str] = None
    last_summary_called_at: Optional[str] = None
    last_risk_call_success: Optional[bool] = None
    last_risk_call_message: Optional[str] = None
    last_risk_called_at: Optional[str] = None


class SystemSettingsUpdateRequest(BaseModel):
    review_provider: str = Field(pattern="^(mock|openai_compatible)$")
    llm_base_url: str = ""
    llm_model: str = ""
    llm_timeout_seconds: int = Field(default=30, ge=1, le=300)
    llm_api_key: Optional[str] = None
    clear_llm_api_key: bool = False


class SystemSettingsTestRequest(BaseModel):
    review_provider: str = Field(pattern="^(mock|openai_compatible)$")
    llm_base_url: str = ""
    llm_model: str = ""
    llm_timeout_seconds: int = Field(default=30, ge=1, le=300)
    llm_api_key: Optional[str] = None


class SystemSettingsTestResponse(BaseModel):
    success: bool
    provider: str
    message: str
