"""System prompt input pipeline - passes through with minimal validation."""

from pydantic import BaseModel, Field, field_validator

from model_governance.pipelines.base import InputPipeline, PipelineResult
from model_governance.trust.levels import TrustLevel


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

    def __init__(self) -> None:
        """Initialize the system prompt pipeline."""
        super().__init__()

    async def process(self, input_data: str) -> PipelineResult:
        """Process system prompt input.

        Args:
            input_data: The system prompt content.

        Returns:
            PipelineResult with CRITICAL trust level and validated content.
        """
        try:
            validated = SystemPromptInput(content=input_data)
        except Exception as e:
            return PipelineResult(
                success=False,
                errors=[f"Validation failed: {e}"],
                blocked=True,
                block_reason="Invalid system prompt format",
            )

        return PipelineResult(
            success=True,
            data=validated.content,
            trust_level=TrustLevel.CRITICAL,
            blocked=False,
            metadata={"source": "system_prompt", "version": validated.version},
        )
