"""System prompt input pipeline - passes through with minimal validation."""

from pydantic import BaseModel, Field, field_validator

from model_governance.core.modes import EnforcementMode
from model_governance.pipelines.base import InputPipeline, PipelineResult
from model_governance.trust.levels import TrustLevel
from model_governance.validators.security import (
    sanitize_content,
    validate_no_injection,
    validate_no_code_execution,
)


class SystemPromptInput(BaseModel):
    """System prompt input schema.

    System prompts are trusted inputs from the system itself,
    so they receive minimal processing.
    """

    content: str = Field(..., min_length=1, max_length=100000, description="System prompt content")
    source: str = Field(default="system", description="Input source identifier")
    version: str | None = Field(default=None, description="Optional version identifier")

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        """Ensure content is not just whitespace."""
        if not v.strip():
            raise ValueError("Content cannot be empty or whitespace only")
        return v


class SystemPromptPipeline(InputPipeline):
    """Pipeline for system prompt validation.

    System prompts pass through with minimal validation since they
    are considered trusted CRITICAL level inputs from the system.
    """

    def __init__(self, mode: EnforcementMode = EnforcementMode.BLOCK) -> None:
        """Initialize the system prompt pipeline.

        Args:
            mode: The enforcement mode.
        """
        super().__init__(mode=mode)

    async def process(
        self,
        input_data: str,
        mode: EnforcementMode | None = None,
    ) -> PipelineResult:
        """Process system prompt input.

        Args:
            input_data: The system prompt content.
            mode: The enforcement mode. Overrides __init__ default.

        Returns:
            PipelineResult with CRITICAL trust level and validated content.
        """
        effective_mode = mode or self._mode

        try:
            validated = SystemPromptInput(content=input_data)
        except Exception as e:
            return PipelineResult(
                success=False,
                errors=[f"Validation failed: {e}"],
                blocked=True,
                block_reason="Invalid system prompt format",
                mode=effective_mode.value,
            )

        # Even system prompts should be validated for obvious security issues
        # This prevents accidental or intentional injection into system prompts
        trust_level = TrustLevel.CRITICAL

        # Check for injection patterns
        injection_result = validate_no_injection(validated.content)
        if not injection_result["valid"]:
            return self._handle_violation(
                injection_result["reason"],
                "Potential prompt injection in system prompt",
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
                "Potentially dangerous code execution pattern in system prompt",
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
            metadata={"source": "system_prompt", "version": validated.version},
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
            trust_level: Optional trust level to include in result.
            pattern: The pattern that triggered the violation (for sanitization).

        Returns:
            PipelineResult appropriate for the mode.
        """
        # For system prompts, default to CRITICAL if not provided
        if trust_level is None:
            trust_level = TrustLevel.CRITICAL

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
