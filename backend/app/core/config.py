from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "工程合同 AI 审查助手"
    app_version: str = "0.3.0"
    app_description: str = "工程合同 AI 审查系统升级版后端，支持文档管理、规则审查、版本留痕与后台管理。"

    database_url: str = "postgresql+psycopg://contract_review:contract_review@localhost:5432/contract_review"

    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 120

    default_admin_username: str = "admin"
    default_admin_password: str = "Admin123456"
    upload_dir: str = "uploads"
    review_provider: str = "mock"
    llm_base_url: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None
    llm_timeout_seconds: int = 30
    report_title: str = "工程合同审查报告"
    ocr_language: str = "chi_sim+eng"
    ocr_render_scale: float = 2.0
    async_ocr_page_threshold: int = 10
    cors_origins: str = "*"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
settings_upload_path = Path(settings.upload_dir)
