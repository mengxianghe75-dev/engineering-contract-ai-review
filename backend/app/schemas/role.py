from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class RoleResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
