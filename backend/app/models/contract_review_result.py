from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ContractReviewResult(Base):
    __tablename__ = "contract_review_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    contract_file_id: Mapped[int] = mapped_column(
        ForeignKey("contract_files.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    extracted_fields: Mapped[dict] = mapped_column(JSON, nullable=False)
    risks: Mapped[list] = mapped_column(JSON, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    latest_version_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("review_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    latest_version_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    contract_file: Mapped["ContractFile"] = relationship()
