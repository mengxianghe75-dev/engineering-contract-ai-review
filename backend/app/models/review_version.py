from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ReviewVersion(Base):
    __tablename__ = "review_versions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    contract_id: Mapped[int] = mapped_column(
        ForeignKey("contract_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    triggered_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    trigger_source: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")
    extracted_fields: Mapped[dict] = mapped_column(JSON, nullable=False)
    risk_items: Mapped[list] = mapped_column(JSON, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    summary_provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    summary_success: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    summary_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    risk_success: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    risk_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    overall_risk_level: Mapped[str] = mapped_column(String(16), nullable=False, default="low")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
