"""Pydantic schemas for type-safe data validation."""

from typing import Any

from pydantic import BaseModel, Field


class SystemPromptInput(BaseModel):
    """System prompt input schema."""

    content: str = Field(..., min_length=1, max_length=100000)
    source: str = Field(default="system")
    version: str | None = None


class UserInput(BaseModel):
    """User input schema."""

    content: str = Field(..., min_length=1, max_length=50000)
    source: str = Field(default="user")
    user_id: str | None = None
    session_id: str | None = None


class ToolInput(BaseModel):
    """Tool input schema."""

    tool_name: str = Field(..., min_length=1, max_length=100)
    parameters: dict[str, Any] = Field(default_factory=dict)
    raw_content: str | None = None
    source: str = Field(default="tool")


class AttachmentInput(BaseModel):
    """Attachment input schema."""

    filename: str = Field(..., min_length=1, max_length=255)
    mime_type: str
    content: str | bytes
    size: int | None = Field(default=None, ge=0)
    source: str = Field(default="attachment")


class Base64Input(BaseModel):
    """Base64 input schema."""

    content: str
    encoding: str = Field(default="utf-8")
    source: str = Field(default="base64")


class GovernanceContext(BaseModel):
    """Context for governance operations."""

    source_type: str
    source_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    trust_level: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
