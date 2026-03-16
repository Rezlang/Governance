"""Enforcement modes for content handling in the governance system."""

from enum import Enum


class EnforcementMode(Enum):
    """Enforcement modes for content handling.

    Modes determine how the governance system handles policy violations:
    - DETECT: Log warnings but allow content to pass through
    - MODIFY: Remove or sanitize problematic content parts
    - BLOCK: Block entire message (default, current behavior)
    """

    DETECT = "detect"
    """Warn but allow content through."""

    MODIFY = "modify"
    """Remove problematic parts of content."""

    BLOCK = "block"
    """Block entire message (default behavior)."""

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if a string is a valid mode.

        Args:
            value: The mode string to validate.

        Returns:
            True if valid, False otherwise.
        """
        return value in {m.value for m in cls}

    @classmethod
    def default(cls) -> "EnforcementMode":
        """Get the default enforcement mode.

        Returns:
            The default mode (BLOCK).
        """
        return cls.BLOCK
