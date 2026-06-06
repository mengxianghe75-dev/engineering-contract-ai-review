from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ContractFile(Base):
    __tablename__ = "contract_files"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    version_root_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("contract_files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    upload_version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded", index=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
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

    parse_result: Mapped["ContractParseResult"] = relationship(
        back_populates="contract_file",
        uselist=False,
        cascade="all, delete-orphan",
    )
    owner: Mapped[Optional["User"]] = relationship(
        foreign_keys=[owner_id],
    )
    updater: Mapped[Optional["User"]] = relationship(
        foreign_keys=[updated_by],
    )
    version_root: Mapped[Optional["ContractFile"]] = relationship(
        remote_side=[id],
        foreign_keys=[version_root_id],
    )
