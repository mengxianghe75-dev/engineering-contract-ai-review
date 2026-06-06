from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class UserListItem(BaseModel):
    id: int
    username: str
    is_active: bool
    roles: list[str]
    created_at: str
    updated_at: str


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    is_active: bool = True
    role_codes: list[str] = Field(min_length=1)


class UserUpdateRequest(BaseModel):
    username: Optional[str] = Field(default=None, min_length=1, max_length=50)
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    is_active: Optional[bool] = None
    role_codes: Optional[list[str]] = None


class UserResponse(BaseModel):
    id: int
    username: str
    is_active: bool
    roles: list[str]
    created_at: str
    updated_at: str
