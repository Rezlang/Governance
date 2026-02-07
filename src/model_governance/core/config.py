"""Configuration management for the model governance system."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrustLevelConfig:
    """Configuration for trust level behavior."""

    default_level: str = "LOW"
    block_below: str = "MEDIUM"
    require_review_below: str = "MEDIUM"


@dataclass
class BlockingConfig:
    """Configuration for content blocking."""

    html_output_enabled: bool = False
    json_output_enabled: bool = True
    block_threshold: float = 0.7
    max_content_length: int = 100000


@dataclass
class CheckerConfig:
    """Configuration for safety checkers."""

    semantic_threshold: float = 0.8
    llm_threshold: float = 0.7
    enable_parallel_checks: bool = True
    timeout_seconds: int = 30


@dataclass
class GovernanceConfig:
    """Main configuration for the governance system."""

    trust: TrustLevelConfig = field(default_factory=TrustLevelConfig)
    blocking: BlockingConfig = field(default_factory=BlockingConfig)
    checker: CheckerConfig = field(default_factory=CheckerConfig)
    custom_policies: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GovernanceConfig":
        """Create configuration from a dictionary."""
        trust_config = TrustLevelConfig(**data.get("trust", {}))
        blocking_config = BlockingConfig(**data.get("blocking", {}))
        checker_config = CheckerConfig(**data.get("checker", {}))
        return cls(
            trust=trust_config,
            blocking=blocking_config,
            checker=checker_config,
            custom_policies=data.get("custom_policies", {}),
        )


def load_config(config_path: str | None = None) -> GovernanceConfig:
    """Load configuration from file or use defaults.

    Args:
        config_path: Optional path to a configuration file.

    Returns:
        GovernanceConfig instance with loaded or default values.
    """
    if config_path:
        import json

        with open(config_path) as f:
            data = json.load(f)
        return GovernanceConfig.from_dict(data)
    return GovernanceConfig()
