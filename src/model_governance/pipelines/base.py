"""Core pipeline interfaces and base classes for the governance system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from model_governance.core.modes import EnforcementMode
from model_governance.trust.levels import TrustLevel

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class PipelineResult:
    """Standard result object for all pipeline stages.

    Attributes:
        success: Whether the pipeline stage succeeded.
        data: The processed data, if successful.
        errors: List of error messages, if any.
        trust_level: The assigned trust level for the data.
        blocked: Whether the content was blocked.
        block_reason: Reason for blocking, if blocked.
        metadata: Additional metadata about the processing.
        mode: The enforcement mode used (detect, modify, block).
        warnings: List of warnings for detect mode.
        modified: Whether content was modified.
        original_content: Original content before modification.
    """

    success: bool
    data: Any = None
    errors: list[str] = field(default_factory=list)
    trust_level: TrustLevel | None = None
    blocked: bool = False
    block_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    mode: str = "block"
    warnings: list[str] = field(default_factory=list)
    modified: bool = False
    original_content: str | None = None

    def add_error(self, error: str) -> None:
        """Add an error to the result.

        Args:
            error: The error message to add.
        """
        self.errors.append(error)
        self.success = False

    def add_warning(self, warning: str) -> None:
        """Add a warning to the result.

        Args:
            warning: The warning message to add.
        """
        self.warnings.append(warning)


class PipelineStage(ABC, Generic[T, R]):
    """Base class for all pipeline stages.

    Pipeline stages can be chained together using the Chain of Responsibility
    pattern. Each stage processes input and passes it to the next stage.
    """

    def __init__(self, next_stage: object = None, mode: EnforcementMode = EnforcementMode.BLOCK) -> None:
        """Initialize the pipeline stage.

        Args:
            next_stage: The next stage in the pipeline chain.
            mode: The enforcement mode.
        """
        self._next = next_stage
        self._mode = mode

    @abstractmethod
    async def process(self, input_data: T) -> PipelineResult:
        """Process input through this stage.

        Args:
            input_data: The input data to process.

        Returns:
            PipelineResult containing the processing outcome.
        """
        pass

    async def _next_process(self, input_data: T) -> PipelineResult:
        """Pass to next stage in chain.

        Args:
            input_data: The input data to pass to the next stage.

        Returns:
            PipelineResult from the next stage, or a default success result.
        """
        if self._next:
            return await self._next.process(input_data)
        return PipelineResult(success=True, data=input_data, mode=self._mode.value)

    def set_next(self, next_stage: "PipelineStage[T, R]") -> "PipelineStage[T, R]":
        """Set the next stage in the pipeline chain.

        Args:
            next_stage: The next stage to set.

        Returns:
            The next stage, for chaining.
        """
        self._next = next_stage
        return next_stage


class InputPipeline(PipelineStage[str, PipelineResult]):
    """Base class for input-specific pipelines.

    Input pipelines validate and process different types of inputs
    (system prompts, user input, tools, attachments, base64).
    """

    async def process(self, input_data: str) -> PipelineResult:
        """Process input data.

        Args:
            input_data: The input string to process.

        Returns:
            PipelineResult with validation and processing results.
        """
        raise NotImplementedError


class OutputPipeline(PipelineStage[str, PipelineResult]):
    """Base class for output safety pipelines.

    Output pipelines validate model outputs for safety and compliance.
    """

    async def process(self, input_data: str) -> PipelineResult:
        """Process output data.

        Args:
            input_data: The output string to validate.

        Returns:
            PipelineResult with safety check results.
        """
        raise NotImplementedError
