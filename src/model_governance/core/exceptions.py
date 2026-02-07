"""Custom exceptions for the model governance system."""


class GovernanceError(Exception):
    """Base exception for all governance-related errors."""

    pass


class PipelineError(GovernanceError):
    """Exception raised when pipeline processing fails."""

    def __init__(self, message: str, stage: str | None = None) -> None:
        self.stage = stage
        super().__init__(f"{stage}: {message}" if stage else message)


class PolicyViolationError(GovernanceError):
    """Exception raised when a policy is violated."""

    def __init__(self, message: str, policy_name: str | None = None) -> None:
        self.policy_name = policy_name
        super().__init__(f"{policy_name}: {message}" if policy_name else message)


class TrustLevelError(GovernanceError):
    """Exception raised for trust level related errors."""

    pass


class ValidationError(GovernanceError):
    """Exception raised when input validation fails."""

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(f"{field}: {message}" if field else message)
