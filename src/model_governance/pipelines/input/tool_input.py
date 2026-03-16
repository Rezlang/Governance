"""Tool input pipeline for tool call validation."""

import json
from typing import Any

from pydantic import BaseModel, Field, field_validator

from model_governance.core.modes import EnforcementMode
from model_governance.pipelines.base import InputPipeline, PipelineResult
from model_governance.trust.classifier import TrustClassifier, TrustContext
from model_governance.trust.levels import TrustLevel
from model_governance.validators.security import sanitize_content, validate_no_sql_injection


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
        mode: EnforcementMode = EnforcementMode.BLOCK,
    ) -> None:
        """Initialize the tool input pipeline.

        Args:
            classifier: Optional trust classifier.
            allowed_tools: Set of allowed tool names. If None, all tools allowed.
            tool_trust_levels: Optional trust levels per tool.
            mode: The enforcement mode.
        """
        super().__init__(mode=mode)
        self._classifier = classifier or TrustClassifier()
        self._allowed_tools = {t.lower() for t in (allowed_tools or set())}
        self._tool_trust_levels = tool_trust_levels or {}

    async def process(
        self,
        input_data: str,
        tool_name: str | None = None,
        parameters: dict[str, Any] | None = None,
        authentication_level: TrustLevel | None = None,
        mode: EnforcementMode | None = None,
    ) -> PipelineResult:
        """Process tool input with validation.

        Args:
            input_data: The tool input (can be JSON string or raw content).
            tool_name: Name of the tool being called.
            parameters: Tool parameters as dict.
            authentication_level: Optional trust level from authentication.
            mode: The enforcement mode.

        Returns:
            PipelineResult with validation results and trust level.
        """
        effective_mode = mode or self._mode

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
                mode=effective_mode.value,
            )

        parsed_tool_name = parsed_tool_name.lower()

        # Validate against allowed tools
        if self._allowed_tools and parsed_tool_name not in self._allowed_tools:
            if effective_mode == EnforcementMode.DETECT:
                return PipelineResult(
                    success=True,
                    data=input_data,
                    blocked=False,
                    warnings=[f"Tool '{parsed_tool_name}' is not allowed"],
                    mode=effective_mode.value,
                )
            elif effective_mode == EnforcementMode.MODIFY:
                return PipelineResult(
                    success=True,
                    data=input_data,
                    blocked=False,
                    warnings=[f"Tool '{parsed_tool_name}' would be blocked"],
                    mode=effective_mode.value,
                )
            else:  # block mode
                return PipelineResult(
                    success=False,
                    errors=[f"Tool '{parsed_tool_name}' is not allowed"],
                    blocked=True,
                    block_reason=f"Tool not in allowlist: {parsed_tool_name}",
                    mode=effective_mode.value,
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
                mode=effective_mode.value,
            )

        # Get trust level for this tool BEFORE validation checks
        tool_trust = self._tool_trust_levels.get(validated.tool_name)

        # Classify trust level
        context = TrustContext(
            source_type="tool_input",
            source_id=validated.tool_name,
            authentication_level=authentication_level or tool_trust,
        )
        trust_level = await self._classifier.classify(context)

        # Validate for SQL injection in database tools
        db_tool_keywords = {"database", "db", "sql", "query", "postgres", "mysql", "sqlite", "mongodb"}
        is_db_tool = any(keyword in validated.tool_name.lower() for keyword in db_tool_keywords)

        if is_db_tool:
            # Validate all string parameters for SQL injection
            for key, value in validated.parameters.items():
                if isinstance(value, str):
                    sql_result = validate_no_sql_injection(value)
                    if not sql_result["valid"]:
                        return self._handle_violation(
                            sql_result["reason"],
                            "Potential SQL injection detected",
                            input_data,
                            effective_mode,
                            trust_level,
                            sql_result.get("pattern"),
                        )

            # Also check raw content if present
            if validated.raw_content:
                sql_result = validate_no_sql_injection(validated.raw_content)
                if not sql_result["valid"]:
                    return self._handle_violation(
                        sql_result["reason"],
                        "Potential SQL injection detected",
                        input_data,
                        effective_mode,
                        trust_level,
                        sql_result.get("pattern"),
                    )

        return PipelineResult(
            success=True,
            data=validated.model_dump(),
            trust_level=trust_level,
            blocked=False,
            mode=effective_mode.value,
            metadata={
                "source": "tool_input",
                "tool_name": validated.tool_name,
                "parameters": validated.parameters,
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
