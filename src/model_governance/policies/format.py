"""Format enforcement policies for structured output."""

import json
from typing import Any

from pydantic import BaseModel, ValidationError

from model_governance.policies.base import Policy, PolicyResult


class JSONEnforcementPolicy(Policy):
    """Policy to enforce valid JSON output format.

    Ensures that output is valid and optionally conforms to a schema.
    """

    def __init__(self, priority: int = 100, schema: type[BaseModel] | dict | None = None) -> None:
        """Initialize the JSON enforcement policy.

        Args:
            priority: Policy priority.
            schema: Optional Pydantic model or JSON schema for validation.
        """
        self._priority = priority
        self._schema_model = schema if isinstance(schema, type) and issubclass(schema, BaseModel) else None
        self._schema_dict = schema if isinstance(schema, dict) else None

    @property
    def name(self) -> str:
        """Policy name."""
        return "json_enforcement"

    @property
    def priority(self) -> int:
        """Policy priority."""
        return self._priority

    async def evaluate(self, content: str, context: dict[str, Any]) -> PolicyResult:
        """Evaluate content for valid JSON format.

        Args:
            content: The content to evaluate.
            context: Additional context for evaluation.

        Returns:
            PolicyResult with the evaluation outcome.
        """
        try:
            data = json.loads(content.strip())
        except json.JSONDecodeError as e:
            return PolicyResult(
                allowed=False,
                reason=f"Invalid JSON format: {e}",
                confidence=1.0,
            )

        if self._schema_model:
            try:
                self._schema_model.model_validate(data)
            except ValidationError as e:
                return PolicyResult(
                    allowed=False,
                    reason=f"JSON does not conform to schema: {e}",
                    confidence=1.0,
                )

        return PolicyResult(allowed=True, reason="Valid JSON format")


class StructuredOutputPolicy(Policy):
    """Policy to enforce structured output formats.

    Supports various structured formats like JSON, XML, YAML, etc.
    """

    def __init__(
        self,
        priority: int = 100,
        format_type: str = "json",
        strict: bool = True,
    ) -> None:
        """Initialize the structured output policy.

        Args:
            priority: Policy priority.
            format_type: The required format type ('json', 'xml', 'yaml', etc.).
            strict: Whether to enforce strict format compliance.
        """
        self._priority = priority
        self._format_type = format_type.lower()
        self._strict = strict

        self._validators: dict[str, Any] = {
            "json": self._validate_json,
            "xml": self._validate_xml,
        }

    @property
    def name(self) -> str:
        """Policy name."""
        return f"structured_output_{self._format_type}"

    @property
    def priority(self) -> int:
        """Policy priority."""
        return self._priority

    async def evaluate(self, content: str, context: dict[str, Any]) -> PolicyResult:
        """Evaluate content for structured format compliance.

        Args:
            content: The content to evaluate.
            context: Additional context for evaluation.

        Returns:
            PolicyResult with the evaluation outcome.
        """
        validator = self._validators.get(self._format_type)

        if validator is None:
            return PolicyResult(allowed=True, reason=f"Format '{self._format_type}' not enforced")

        return await validator(content)

    async def _validate_json(self, content: str) -> PolicyResult:
        """Validate JSON format."""
        try:
            json.loads(content.strip())
            return PolicyResult(allowed=True, reason="Valid JSON format")
        except json.JSONDecodeError as e:
            return PolicyResult(
                allowed=False,
                reason=f"Invalid JSON format: {e}",
                confidence=1.0,
            )

    async def _validate_xml(self, content: str) -> PolicyResult:
        """Validate XML format."""
        content = content.strip()

        if not content.startswith("<") or not content.endswith(">"):
            return PolicyResult(
                allowed=False,
                reason="Content does not appear to be XML",
                confidence=0.8,
            )

        if self._strict:
            try:
                import xml.etree.ElementTree as ET

                ET.fromstring(content)
                return PolicyResult(allowed=True, reason="Valid XML format")
            except ET.ParseError as e:
                return PolicyResult(
                    allowed=False,
                    reason=f"Invalid XML format: {e}",
                    confidence=1.0,
                )

        return PolicyResult(allowed=True, reason="Content appears to be XML")


class MaxLengthPolicy(Policy):
    """Policy to enforce maximum content length.

    Useful for preventing excessively long outputs.
    """

    def __init__(self, priority: int = 50, max_length: int = 10000) -> None:
        """Initialize the max length policy.

        Args:
            priority: Policy priority.
            max_length: Maximum allowed content length.
        """
        self._priority = priority
        self._max_length = max_length

    @property
    def name(self) -> str:
        """Policy name."""
        return "max_length"

    @property
    def priority(self) -> int:
        """Policy priority."""
        return self._priority

    async def evaluate(self, content: str, context: dict[str, Any]) -> PolicyResult:
        """Evaluate content length.

        Args:
            content: The content to evaluate.
            context: Additional context for evaluation.

        Returns:
            PolicyResult with the evaluation outcome.
        """
        length = len(content)

        if length > self._max_length:
            return PolicyResult(
                allowed=False,
                reason=f"Content exceeds maximum length of {self._max_length} characters (got {length})",
                confidence=1.0,
            )

        return PolicyResult(allowed=True, reason=f"Content length within limit ({length}/{self._max_length})")
