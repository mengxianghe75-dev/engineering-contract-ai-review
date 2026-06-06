from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ReviewLogItem(BaseModel):
    id: int
    operator_id: Optional[int] = None
    operator_username: Optional[str] = None
    target_type: str
    target_id: Optional[int] = None
    action_type: str
    action_detail: Optional[str] = None
    created_at: str
