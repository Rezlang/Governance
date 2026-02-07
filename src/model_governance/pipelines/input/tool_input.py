"""Tool input pipeline for tool call validation."""

import json
from typing import Any

from pydantic import BaseModel, Field, field_validator

from model_governance.pipelines.base import InputPipeline, PipelineResult
from model_governance.trust.classifier import TrustClassifier, TrustContext
from model_governance.trust.levels import TrustLevel


class ToolInput(BaseModel):
    """Tool input schema for tool calls."""

    tool_name: str = Field(..., min_length=1, max_length=100, description="Name of the tool being called")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    raw_content: str | None = Field(default=None, description="Raw content if provided as string")
    source: str = Field(default="tool", description="Input source identifier")

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        """Validate tool name format."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Tool name must contain only alphanumeric characters, hyphens, and underscores")
        return v.lower()


class ToolInputPipeline(InputPipeline):
    """Pipeline for tool input validation.

    Tool inputs are validated for proper format and receive
    MEDIUM trust level by default (configurable per tool).
    """

    def __init__(
        self,
        classifier: TrustClassifier | None = None,
        allowed_tools: set[str] | None = None,
        tool_trust_levels: dict[str, TrustLevel] | None = None,
    ) -> None:
        """Initialize the tool input pipeline.

        Args:
            classifier: Optional trust classifier.
            allowed_tools: Set of allowed tool names. If None, all tools allowed.
            tool_trust_levels: Optional trust levels per tool.
        """
        super().__init__()
        self._classifier = classifier or TrustClassifier()
        self._allowed_tools = {t.lower() for t in (allowed_tools or set())}
        self._tool_trust_levels = tool_trust_levels or {}

    async def process(
        self,
        input_data: str,
        tool_name: str | None = None,
        parameters: dict[str, Any] | None = None,
        authentication_level: TrustLevel | None = None,
    ) -> PipelineResult:
        """Process tool input with validation.

        Args:
            input_data: The tool input (can be JSON string or raw content).
            tool_name: Name of the tool being called.
            parameters: Tool parameters as dict.
            authentication_level: Optional trust level from authentication.

        Returns:
            PipelineResult with validation results and trust level.
        """
        # Try to parse as JSON for structured tool input
        parsed_tool_name = tool_name
        parsed_params = parameters or {}

        if input_data.strip().startswith(("{", "[")):
            try:
                data = json.loads(input_data)
                if isinstance(data, dict):
                    parsed_tool_name = data.get("tool") or data.get("tool_name", parsed_tool_name)
                    parsed_params = data.get("parameters", data.get("args", parsed_params))
            except json.JSONDecodeError:
                pass

        if not parsed_tool_name:
            return PipelineResult(
                success=False,
                errors=["Tool name is required"],
                blocked=True,
                block_reason="Tool name not provided",
            )

        parsed_tool_name = parsed_tool_name.lower()

        # Validate against allowed tools
        if self._allowed_tools and parsed_tool_name not in self._allowed_tools:
            return PipelineResult(
                success=False,
                errors=[f"Tool '{parsed_tool_name}' is not allowed"],
                blocked=True,
                block_reason=f"Tool not in allowlist: {parsed_tool_name}",
            )

        try:
            validated = ToolInput(
                tool_name=parsed_tool_name,
                parameters=parsed_params,
                raw_content=input_data if not input_data.strip().startswith(("{", "[")) else None,
            )
        except Exception as e:
            return PipelineResult(
                success=False,
                errors=[f"Validation failed: {e}"],
                blocked=True,
                block_reason="Invalid tool input format",
            )

        # Get trust level for this tool
        tool_trust = self._tool_trust_levels.get(validated.tool_name)

        # Classify trust level
        context = TrustContext(
            source_type="tool_input",
            source_id=validated.tool_name,
            authentication_level=authentication_level or tool_trust,
        )
        trust_level = await self._classifier.classify(context)

        return PipelineResult(
            success=True,
            data=validated.model_dump(),
            trust_level=trust_level,
            blocked=False,
            metadata={
                "source": "tool_input",
                "tool_name": validated.tool_name,
                "parameters": validated.parameters,
            },
        )
