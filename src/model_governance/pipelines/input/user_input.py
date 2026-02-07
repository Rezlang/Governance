"""User input pipeline with full validation and trust classification."""

from pydantic import BaseModel, Field, field_validator

from model_governance.pipelines.base import InputPipeline, PipelineResult
from model_governance.trust.classifier import TrustClassifier, TrustContext
from model_governance.trust.levels import TrustLevel
from model_governance.validators.security import validate_no_injection, validate_length


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

    def __init__(self, classifier: TrustClassifier | None = None) -> None:
        """Initialize the user input pipeline.

        Args:
            classifier: Optional trust classifier. Uses default if not provided.
        """
        super().__init__()
        self._classifier = classifier or TrustClassifier()

    async def process(
        self,
        input_data: str,
        user_id: str | None = None,
        historical_trust: float | None = None,
        authentication_level: TrustLevel | None = None,
    ) -> PipelineResult:
        """Process user input with validation and trust classification.

        Args:
            input_data: The user input content.
            user_id: Optional user identifier.
            historical_trust: Optional historical trust score (0.0 to 1.0).
            authentication_level: Optional trust level from authentication.

        Returns:
            PipelineResult with validation results and assigned trust level.
        """
        try:
            validated = UserInput(content=input_data, user_id=user_id)
        except Exception as e:
            return PipelineResult(
                success=False,
                errors=[f"Validation failed: {e}"],
                blocked=True,
                block_reason="Invalid user input format",
            )

        # Validate length
        length_result = validate_length(validated.content, max_length=50000)
        if not length_result["valid"]:
            return PipelineResult(
                success=False,
                errors=[length_result["reason"]],
                blocked=True,
                block_reason="Content too long",
            )

        # Check for injection patterns
        injection_result = validate_no_injection(validated.content)
        if not injection_result["valid"]:
            return PipelineResult(
                success=False,
                errors=[injection_result["reason"]],
                blocked=True,
                block_reason="Potential prompt injection detected",
            )

        # Classify trust level
        context = TrustContext(
            source_type="user_input",
            source_id=user_id,
            historical_trust=historical_trust,
            authentication_level=authentication_level,
        )
        trust_level = await self._classifier.classify(context)

        return PipelineResult(
            success=True,
            data=validated.content,
            trust_level=trust_level,
            blocked=False,
            metadata={
                "source": "user_input",
                "user_id": user_id,
                "historical_trust": historical_trust,
            },
        )
