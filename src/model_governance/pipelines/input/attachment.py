"""Attachment pipeline for file input validation."""

import base64

from pydantic import BaseModel, Field, field_validator

from model_governance.core.modes import EnforcementMode
from model_governance.pipelines.base import InputPipeline, PipelineResult
from model_governance.trust.classifier import TrustClassifier, TrustContext
from model_governance.trust.levels import TrustLevel


class AttachmentInput(BaseModel):
    """Attachment input schema for file uploads."""

    filename: str = Field(..., min_length=1, max_length=255, description="File name")
    mime_type: str = Field(..., description="MIME type of the file")
    content: str | bytes = Field(..., description="File content (base64 string or bytes)")
    size: int | None = Field(default=None, ge=0, description="File size in bytes")
    source: str = Field(default="attachment", description="Input source identifier")

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Validate filename doesn't contain path traversal."""
        if ".." in v or v.startswith(("/", "\\")):
            raise ValueError("Filename contains invalid path characters")
        return v

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, v: str) -> str:
        """Validate MIME type format."""
        if "/" not in v:
            raise ValueError("Invalid MIME type format")
        return v.lower()


class AttachmentPipeline(InputPipeline):
    """Pipeline for attachment validation and processing.

    Attachments receive LOW trust by default due to potential
    security risks from file uploads.
    """

    def __init__(
        self,
        classifier: TrustClassifier | None = None,
        max_size: int = 10 * 1024 * 1024,  # 10MB default
        allowed_mime_types: set[str] | None = None,
        blocked_mime_types: set[str] | None = None,
        mode: EnforcementMode = EnforcementMode.BLOCK,
    ) -> None:
        """Initialize the attachment pipeline.

        Args:
            classifier: Optional trust classifier.
            max_size: Maximum file size in bytes.
            allowed_mime_types: Set of allowed MIME types. If None, basic types allowed.
            blocked_mime_types: Set of blocked MIME types.
            mode: The enforcement mode.
        """
        super().__init__(mode=mode)
        self._classifier = classifier or TrustClassifier()
        self._max_size = max_size
        self._allowed_mime_types = {m.lower() for m in (allowed_mime_types or set())}
        self._blocked_mime_types = {m.lower() for m in (
            blocked_mime_types or {
                "application/x-executable",
                "application/x-msdownload",
                "application/x-msdos-program",
            }
        )}

        # Default allowed types if none specified
        if not self._allowed_mime_types:
            self._allowed_mime_types = {
                "text/plain",
                "text/csv",
                "application/json",
                "application/pdf",
                "image/png",
                "image/jpeg",
                "image/gif",
                "image/webp",
            }

    async def process(
        self,
        input_data: str,
        filename: str,
        mime_type: str,
        size: int | None = None,
        authentication_level: TrustLevel | None = None,
        mode: EnforcementMode | None = None,
    ) -> PipelineResult:
        """Process attachment with validation.

        Args:
            input_data: Base64 encoded file content.
            filename: Name of the file.
            mime_type: MIME type of the file.
            size: Optional file size in bytes.
            authentication_level: Optional trust level from authentication.
            mode: The enforcement mode. Overrides __init__ default.

        Returns:
            PipelineResult with validation results and trust level.
        """
        effective_mode = mode or self._mode
        mime_type = mime_type.lower()

        # Check blocked MIME types
        if mime_type in self._blocked_mime_types:
            return PipelineResult(
                success=False,
                errors=[f"File type '{mime_type}' is blocked"],
                blocked=True,
                block_reason=f"Blocked file type: {mime_type}",
                mode=effective_mode.value,
            )

        # Check allowed MIME types
        if self._allowed_mime_types and mime_type not in self._allowed_mime_types:
            return PipelineResult(
                success=False,
                errors=[f"File type '{mime_type}' is not allowed"],
                blocked=True,
                block_reason=f"File type not in allowlist: {mime_type}",
                mode=effective_mode.value,
            )

        # Decode base64 content
        try:
            content_bytes = base64.b64decode(input_data, validate=True)
        except Exception:
            return PipelineResult(
                success=False,
                errors=["Invalid base64 encoding"],
                blocked=True,
                block_reason="Invalid base64 content",
                mode=effective_mode.value,
            )

        actual_size = len(content_bytes)

        # Check file size
        if size is not None and actual_size != size:
            return PipelineResult(
                success=False,
                errors=[f"Size mismatch: declared {size}, actual {actual_size}"],
                blocked=True,
                block_reason="File size mismatch",
                mode=effective_mode.value,
            )

        if actual_size > self._max_size:
            return PipelineResult(
                success=False,
                errors=[f"File too large: {actual_size} bytes (max {self._max_size})"],
                blocked=True,
                block_reason="File exceeds size limit",
                mode=effective_mode.value,
            )

        try:
            validated = AttachmentInput(
                filename=filename,
                mime_type=mime_type,
                content=content_bytes,
                size=actual_size,
            )
        except Exception as e:
            return PipelineResult(
                success=False,
                errors=[f"Validation failed: {e}"],
                blocked=True,
                block_reason="Invalid attachment format",
                mode=effective_mode.value,
            )

        # Classify trust level (LOW for attachments)
        context = TrustContext(
            source_type="attachment",
            source_id=validated.filename,
            authentication_level=authentication_level,
        )
        trust_level = await self._classifier.classify(context)

        return PipelineResult(
            success=True,
            data=validated.model_dump(),
            trust_level=trust_level,
            blocked=False,
            mode=effective_mode.value,
            metadata={
                "source": "attachment",
                "filename": validated.filename,
                "mime_type": validated.mime_type,
                "size": validated.size,
            },
        )
