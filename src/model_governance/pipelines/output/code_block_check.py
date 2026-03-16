"""Code block safety check pipeline for output validation.

This module provides a checker that detects potentially dangerous code
execution patterns within markdown code blocks in model outputs.
"""

import re
from typing import Protocol, runtime_checkable

from model_governance.pipelines.base import OutputPipeline, PipelineResult
from model_governance.validators.security import CODE_EXECUTION_PATTERNS


@runtime_checkable
class CodeBlockChecker(Protocol):
    """Protocol for code block safety checkers.

    Code block checkers scan markdown code blocks for dangerous
    code execution patterns.
    """

    async def check(self, content: str, context: dict) -> tuple[bool, str, float]:
        """Check content for dangerous code patterns in code blocks.

        Args:
            content: The content to check.
            context: Additional context for the check.

        Returns:
            A tuple of (is_safe, reason, confidence).
        """
        ...


class PatternBasedCodeBlockChecker:
    """Pattern-based code block checker implementation.

    Scans markdown code blocks for dangerous code execution patterns
    like eval(), exec(), os.system, subprocess calls, etc.
    """

    def __init__(
        self,
        patterns: list[str] | None = None,
        block_unsafe_code: bool = True,
    ) -> None:
        """Initialize the code block checker.

        Args:
            patterns: Optional custom patterns to check. Uses defaults if not provided.
            block_unsafe_code: Whether to block unsafe code patterns.
        """
        self._patterns = patterns or CODE_EXECUTION_PATTERNS
        self._block_unsafe = block_unsafe_code
        self._code_block_pattern = re.compile(
            r'```[\w]*\n([\s\S]*?)```',  # Matches ```language\ncode\n```
            re.MULTILINE | re.IGNORECASE
        )

    async def check(
        self, content: str, context: dict | None = None
    ) -> tuple[bool, str, float]:
        """Check content for dangerous code patterns in code blocks.

        Args:
            content: The content to check.
            context: Additional context.

        Returns:
            Tuple of (is_safe, reason, confidence).
        """
        context = context or {}

        # Find all code blocks in the content
        code_blocks = self._code_block_pattern.findall(content)

        if not code_blocks:
            return True, "No code blocks detected", 1.0

        # Check each code block for dangerous patterns
        for idx, code_block in enumerate(code_blocks, 1):
            code_lower = code_block.lower()

            for pattern in self._patterns:
                if pattern.lower() in code_lower:
                    confidence = 0.9  # High confidence for direct pattern matches
                    reason = (
                        f"Code block {idx} contains dangerous pattern: '{pattern}'. "
                        f"Code execution in model outputs poses security risks."
                    )
                    return False, reason, confidence

        return True, f"Checked {len(code_blocks)} code block(s), no dangerous patterns found", 1.0


class CodeBlockCheckPipeline(OutputPipeline):
    """Code block safety check pipeline.

    Scans markdown code blocks for dangerous code execution patterns
    to prevent code injection attacks via model outputs.
    """

    def __init__(
        self,
        checker: CodeBlockChecker | None = None,
        block_on_detection: bool = True,
    ) -> None:
        """Initialize the code block check pipeline.

        Args:
            checker: Optional code block checker. Uses default if not provided.
            block_on_detection: Whether to block content when dangerous patterns are detected.
        """
        super().__init__()
        self._checker = checker or PatternBasedCodeBlockChecker()
        self._block_on_detection = block_on_detection

    async def process(self, input_data: str) -> PipelineResult:
        """Process output through code block safety check.

        Args:
            input_data: The output to check.

        Returns:
            PipelineResult with safety check results.
        """
        is_safe, reason, confidence = await self._checker.check(input_data, {})

        if not is_safe and self._block_on_detection:
            return PipelineResult(
                success=False,
                errors=[reason],
                blocked=True,
                block_reason=f"Code block safety check failed: {reason}",
                metadata={
                    "method": "code_block_check",
                    "confidence": confidence,
                },
            )

        # If detect mode (block_on_detection=False), still pass through with warning
        if not is_safe:
            return PipelineResult(
                success=True,
                data=input_data,
                warnings=[f"[DETECTED] {reason}"],
                metadata={
                    "method": "code_block_check",
                    "confidence": confidence,
                    "violation_detected": True,
                },
            )

        return await self._next_process(input_data)
