"""Abstract base classes for governance components."""

from abc import ABC, abstractmethod
from typing import Any


class GovernanceComponent(ABC):
    """Base class for all governance system components."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the component with optional configuration.

        Args:
            **kwargs: Optional configuration parameters.
        """
        self._config = kwargs

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the component. Called before first use."""

        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the component and release resources."""

        pass
