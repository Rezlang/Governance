"""User input pipeline with full validation and trust classification."""

from pydantic import BaseModel, Field, field_validator

from model_governance.core.modes import EnforcementMode
from model_governance.pipelines.base import InputPipeline, PipelineResult
from model_governance.trust.classifier import TrustClassifier, TrustContext
from model_governance.trust.levels import TrustLevel
from model_governance.validators.security import (
    sanitize_content,
    validate_length,
    validate_no_injection,
    validate_no_code_execution,
)


class UserInput(BaseModel):
    """User input schema with validation."""

    content: str = Field(..., min_length=1, max_length=50000, description="User input content")
    source: str = Field(default="user", description="Input source identifier")
    user_id: str | None = Field(default=None, description="Optional user identifier")
    session_id: str | None = Field(default=None, description="Optional session identifier")

    @field_validator("content")
    @classmethod
    def validate_no_control_characters(cls, v: str) -> str:
        """Remove potentially harmful control characters."""
        harmful_controls = {"\x00", "\x01", "\x02", "\x03", "\x04", "\x05"}
        if any(c in v for c in harmful_controls):
            raise ValueError("Content contains harmful control characters")
        return v


class UserInputPipeline(InputPipeline):
    """Pipeline for user input validation and processing.

    User inputs receive full validation and trust classification
    based on authentication and historical trust scores.
    """

    def __init__(self, classifier: TrustClassifier | None = None, mode: EnforcementMode = EnforcementMode.BLOCK) -> None:
        """Initialize the user input pipeline.

        Args:
            classifier: Optional trust classifier. Uses default if not provided.
            mode: The enforcement mode.
        """
        super().__init__(mode=mode)
        self._classifier = classifier or TrustClassifier()

    async def process(
        self,
        input_data: str,
        user_id: str | None = None,
        historical_trust: float | None = None,
        authentication_level: TrustLevel | None = None,
        mode: EnforcementMode | None = None,
    ) -> PipelineResult:
        """Process user input with validation and trust classification.

        Args:
            input_data: The user input content.
            user_id: Optional user identifier.
            historical_trust: Optional historical trust score (0.0 to 1.0).
            authentication_level: Optional trust level from authentication.
            mode: The enforcement mode. Overrides __init__ default.

        Returns:
            PipelineResult with validation results and assigned trust level.
        """
        effective_mode = mode or self._mode

        try:
            validated = UserInput(content=input_data, user_id=user_id)
        except Exception as e:
            return PipelineResult(
                success=False,
                errors=[f"Validation failed: {e}"],
                blocked=True,
                block_reason="Invalid user input format",
                mode=effective_mode.value,
            )

        # Classify trust level FIRST, before validation checks
        context = TrustContext(
            source_type="user_input",
            source_id=user_id,
            historical_trust=historical_trust,
            authentication_level=authentication_level,
        )
        trust_level = await self._classifier.classify(context)

        # Validate length
        length_result = validate_length(validated.content, max_length=50000)
        if not length_result["valid"]:
            return self._handle_violation(
                length_result["reason"],
                "Content too long",
                validated.content,
                effective_mode,
                trust_level,
                None,  # No pattern for length violations
            )

        # Check for injection patterns
        injection_result = validate_no_injection(validated.content)
        if not injection_result["valid"]:
            return self._handle_violation(
                injection_result["reason"],
                "Potential prompt injection detected",
                validated.content,
                effective_mode,
                trust_level,
                injection_result.get("pattern"),
            )

        # Check for code execution patterns
        code_execution_result = validate_no_code_execution(validated.content)
        if not code_execution_result["valid"]:
            return self._handle_violation(
                code_execution_result["reason"],
                "Potentially dangerous code execution pattern detected",
                validated.content,
                effective_mode,
                trust_level,
                code_execution_result.get("pattern"),
            )

        return PipelineResult(
            success=True,
            data=validated.content,
            trust_level=trust_level,
            blocked=False,
            mode=effective_mode.value,
            metadata={
                "source": "user_input",
                "user_id": user_id,
                "historical_trust": historical_trust,
            },
        )

    def _handle_violation(
        self,
        reason: str,
        block_reason: str,
        content: str,
        mode: EnforcementMode,
        trust_level: int | None = None,
        pattern: str | None = None,
    ) -> PipelineResult:
        """Handle a policy violation based on the enforcement mode.

        Args:
            reason: Detailed reason for the violation.
            block_reason: Short block reason.
            content: The content that caused the violation.
            mode: The enforcement mode.
            trust_level: Optional trust level to include in result for audit purposes.
            pattern: The pattern that triggered the violation (for sanitization).

        Returns:
            PipelineResult appropriate for the mode.
        """
        if mode == EnforcementMode.DETECT:
            return PipelineResult(
                success=True,
                data=content,
                blocked=False,
                warnings=[reason],
                trust_level=trust_level,
                mode=mode.value,
                metadata={"violation_detected": True},
            )
        elif mode == EnforcementMode.MODIFY:
            # Actually sanitize the content by removing the problematic pattern
            if pattern:
                sanitized = sanitize_content(content, pattern)
                modified_content = sanitized["sanitized"]
                modified = sanitized["modified"]
                replacements_count = sanitized["replacements_count"]

                warning = f"[MODIFIED] {reason} - Replaced '{pattern}' with '[REDACTED]' ({replacements_count} occurrence(s))"
            else:
                # No specific pattern to sanitize, return original with warning
                modified_content = content
                modified = False
                warning = f"[WOULD MODIFY] {reason} - No specific pattern to sanitize"

            return PipelineResult(
                success=True,
                data=modified_content,
                blocked=False,
                warnings=[warning],
                trust_level=trust_level,
                mode=mode.value,
                modified=modified,
                original_content=content if modified else None,
                metadata={
                    "modification_needed": True,
                    "pattern_removed": pattern,
                    "replacements_count": replacements_count if pattern else 0,
                },
            )
        else:  # block mode (default)
            return PipelineResult(
                success=False,
                errors=[reason],
                blocked=True,
                block_reason=block_reason,
                trust_level=trust_level,
                mode=mode.value,
            )
