"""Base64 content pipeline for encoded input validation."""

import base64

from pydantic import BaseModel, Field

from model_governance.core.modes import EnforcementMode
from model_governance.pipelines.base import InputPipeline, PipelineResult
from model_governance.trust.classifier import TrustClassifier, TrustContext
from model_governance.trust.levels import TrustLevel


class Base64Input(BaseModel):
    """Base64 encoded input schema."""

    content: str = Field(..., description="Base64 encoded content")
    encoding: str = Field(default="utf-8", description="Expected text encoding after decoding")
    source: str = Field(default="base64", description="Input source identifier")


class Base64Pipeline(InputPipeline):
    """Pipeline for base64 encoded content validation.

    Base64 content receives LOW trust by default and is validated
    for proper encoding and content inspection.
    """

    def __init__(
        self,
        classifier: TrustClassifier | None = None,
        max_decoded_size: int = 1024 * 1024,  # 1MB default
        allow_binary: bool = False,
        mode: EnforcementMode = EnforcementMode.BLOCK,
    ) -> None:
        """Initialize the base64 pipeline.

        Args:
            classifier: Optional trust classifier.
            max_decoded_size: Maximum decoded content size in bytes.
            allow_binary: Whether to allow binary content after decoding.
            mode: The enforcement mode.
        """
        super().__init__(mode=mode)
        self._classifier = classifier or TrustClassifier()
        self._max_decoded_size = max_decoded_size
        self._allow_binary = allow_binary

    async def process(
        self,
        input_data: str,
        encoding: str = "utf-8",
        authentication_level: TrustLevel | None = None,
        mode: EnforcementMode | None = None,
    ) -> PipelineResult:
        """Process base64 encoded content with validation.

        Args:
            input_data: Base64 encoded content string.
            encoding: Expected text encoding after decoding.
            authentication_level: Optional trust level from authentication.
            mode: The enforcement mode.

        Returns:
            PipelineResult with decoded content and trust level.
        """
        effective_mode = mode or self._mode

        # Validate base64 format
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

        # Check size
        if len(content_bytes) > self._max_decoded_size:
            return PipelineResult(
                success=False,
                errors=[
                    f"Decoded content too large: {len(content_bytes)} bytes "
                    f"(max {self._max_decoded_size})"
                ],
                blocked=True,
                block_reason="Decoded content exceeds size limit",
                mode=effective_mode.value,
            )

        # Try to decode as text
        decoded_content: str | bytes
        try:
            decoded_content = content_bytes.decode(encoding)
        except UnicodeDecodeError:
            if self._allow_binary:
                decoded_content = content_bytes
            else:
                return PipelineResult(
                    success=False,
                    errors=[f"Content cannot be decoded as {encoding}"],
                    blocked=True,
                    block_reason="Binary content not allowed",
                    mode=effective_mode.value,
                )

        try:
            validated = Base64Input(content=input_data, encoding=encoding)
        except Exception as e:
            return PipelineResult(
                success=False,
                errors=[f"Validation failed: {e}"],
                blocked=True,
                block_reason="Invalid base64 input format",
                mode=effective_mode.value,
            )

        # Inspect decoded content for potential issues
        decoded_str = decoded_content if isinstance(decoded_content, str) else "<binary>"

        # Check for suspicious patterns
        if "<script>" in decoded_str.lower() or "javascript:" in decoded_str.lower():
            return PipelineResult(
                success=False,
                errors=["Potentially malicious content detected"],
                blocked=True,
                block_reason="Suspicious content pattern detected",
                mode=effective_mode.value,
            )

        # Classify trust level
        context = TrustContext(
            source_type="base64",
            authentication_level=authentication_level,
        )
        trust_level = await self._classifier.classify(context)

        return PipelineResult(
            success=True,
            data={"decoded": decoded_content, "original": validated.content, "encoding": encoding},
            trust_level=trust_level,
            blocked=False,
            mode=effective_mode.value,
            metadata={
                "source": "base64",
                "encoding": encoding,
                "decoded_size": len(content_bytes),
                "is_binary": isinstance(decoded_content, bytes),
            },
        )
