from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ContractParseResult(Base):
    __tablename__ = "contract_parse_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    contract_file_id: Mapped[int] = mapped_column(
        ForeignKey("contract_files.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    parse_status: Mapped[str] = mapped_column(String(length=32), nullable=False, default="completed")
    parse_mode: Mapped[str] = mapped_column(String(length=32), nullable=False, default="text")
    parse_notice: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parse_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    contract_file: Mapped["ContractFile"] = relationship(back_populates="parse_result")
