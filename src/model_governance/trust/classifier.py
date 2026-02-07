"""Trust level classification based on input source and context."""

from pydantic import BaseModel, Field, field_validator

from model_governance.trust.levels import TrustLevel


class TrustContext(BaseModel):
    """Context for trust classification.

    Attributes:
        source_type: The type of input source.
        source_id: Optional identifier for the specific source.
        authentication_level: Optional trust level from authentication.
        historical_trust: Historical trust score (0.0 to 1.0).
        metadata: Additional context for classification.
    """

    source_type: str = Field(..., description="Type of input source")
    source_id: str | None = Field(default=None, description="Optional source identifier")
    authentication_level: TrustLevel | None = Field(default=None, description="Auth trust level")
    historical_trust: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Historical trust score"
    )
    metadata: dict[str, object] = Field(default_factory=dict, description="Additional context")

    @field_validator("authentication_level", mode="before")
    @classmethod
    def validate_trust_level(cls, v: object) -> TrustLevel | None:
        """Validate authentication level is a TrustLevel."""
        if v is None:
            return None
        if isinstance(v, TrustLevel):
            return v
        if isinstance(v, str):
            try:
                return TrustLevel[v.upper()]
            except KeyError:
                return None
        if isinstance(v, int):
            try:
                return TrustLevel(v)
            except ValueError:
                return None
        return None


class TrustClassifier:
    """Classifies trust levels based on context and source type.

    The classifier uses rules to determine appropriate trust levels
    for different types of inputs.
    """

    def __init__(self, default_level: TrustLevel = TrustLevel.LOW) -> None:
        """Initialize the trust classifier.

        Args:
            default_level: Default trust level for unknown sources.
        """
        self._default_level = default_level
        self._rules: dict[str, callable] = {
            "system_prompt": self._classify_system_prompt,
            "system": self._classify_system_prompt,
            "user_input": self._classify_user_input,
            "user": self._classify_user_input,
            "tool_input": self._classify_tool_input,
            "tool": self._classify_tool_input,
            "attachment": self._classify_attachment,
            "base64": self._classify_base64,
        }

    async def classify(self, context: TrustContext) -> TrustLevel:
        """Classify trust level based on context.

        Args:
            context: The trust context for classification.

        Returns:
            The classified trust level.
        """
        rule = self._rules.get(context.source_type.lower())
        if rule:
            return await rule(context)
        return self._default_level

    async def _classify_system_prompt(self, context: TrustContext) -> TrustLevel:
        """System prompts get highest trust.

        Args:
            context: The trust context.

        Returns:
            TrustLevel.CRITICAL for system prompts.
        """
        return TrustLevel.CRITICAL

    async def _classify_user_input(self, context: TrustContext) -> TrustLevel:
        """User input based on authentication and history.

        Args:
            context: The trust context.

        Returns:
            Trust level based on auth and historical trust.
        """
        if context.authentication_level is not None:
            return context.authentication_level
        if context.historical_trust is not None:
            if context.historical_trust > 0.9:
                return TrustLevel.HIGH
            if context.historical_trust > 0.7:
                return TrustLevel.MEDIUM
            if context.historical_trust > 0.5:
                return TrustLevel.LOW
        return self._default_level

    async def _classify_tool_input(self, context: TrustContext) -> TrustLevel:
        """Tool input gets medium trust by default.

        Can be overridden by authentication level if provided.

        Args:
            context: The trust context.

        Returns:
            TrustLevel.MEDIUM or authenticated level.
        """
        if context.authentication_level is not None:
            return context.authentication_level
        return TrustLevel.MEDIUM

    async def _classify_attachment(self, context: TrustContext) -> TrustLevel:
        """Attachments require scrutiny - low trust.

        Args:
            context: The trust context.

        Returns:
            TrustLevel.LOW for attachments.
        """
        if context.authentication_level is not None:
            return min(context.authentication_level, TrustLevel.MEDIUM)
        return TrustLevel.LOW

    async def _classify_base64(self, context: TrustContext) -> TrustLevel:
        """Base64 content is treated with low trust.

        Args:
            context: The trust context.

        Returns:
            TrustLevel.LOW for base64 content.
        """
        if context.authentication_level is not None:
            return min(context.authentication_level, TrustLevel.MEDIUM)
        return TrustLevel.LOW

    def register_rule(self, source_type: str, rule: callable) -> None:
        """Register a custom classification rule.

        Args:
            source_type: The source type this rule handles.
            rule: An async callable that takes TrustContext and returns TrustLevel.
        """
        self._rules[source_type.lower()] = rule
