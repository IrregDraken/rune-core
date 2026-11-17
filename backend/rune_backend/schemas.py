from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class DeviceRegistration(BaseModel):
    device_name: str = Field(min_length=1, max_length=80)
    platform: Literal["android", "ios", "windows", "macos", "linux", "web"]
    app_version: str = Field(default="unknown", max_length=40)
    capabilities: list[str] = Field(default_factory=list, max_length=100)
    public_key: str | None = Field(default=None, max_length=4096)


class DeviceHeartbeat(BaseModel):
    app_version: str | None = Field(default=None, max_length=40)
    capabilities: list[str] | None = Field(default=None, max_length=100)
    status: Literal["online", "idle", "busy"] = "online"


class TaskCreate(BaseModel):
    device_id: UUID
    capability: str = Field(min_length=1, max_length=100)
    arguments: dict[str, Any] = Field(default_factory=dict)
    expires_in_seconds: int = Field(default=60, ge=5, le=3600)
    requires_approval: bool = True


class TaskResultInput(BaseModel):
    status: Literal["completed", "failed", "blocked", "uncertain"]
    output: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = Field(default=None, max_length=100)


class TaskView(BaseModel):
    id: UUID
    status: str
    capability: str
    created_at: datetime | None = None
