"""Model governance system for LLM safety and compliance.

This package provides a comprehensive system for governing model inputs and outputs,
including trust level classification, policy enforcement, and safety checks.

Example:
    ```python
    from model_governance import (
        GovernanceSystem,
        TrustLevel,
        PolicyRegistry,
        CompositeOutputPipeline,
    )

    # Create a governance system
    system = GovernanceSystem()

    # Process user input
    result = await system.process_input(
        source="user_input",
        content="Hello, how are you?",
        trust_level="medium"
    )

    # Process model output
    result = await system.process_output(
        content="Here is the information you requested."
    )
    ```
"""

__version__ = "0.1.0"
__author__ = "Model Governance Team"

# Core exports
from model_governance.core import (
    GovernanceConfig,
    CheckerConfig,
    BlockingConfig,
    TrustLevelConfig,
    GovernanceError,
    PipelineError,
    PolicyViolationError,
    TrustLevelError,
    ValidationError,
    load_config,
)

# Trust level exports
from model_governance.trust import (
    TrustLevel,
    TrustContext,
    TrustClassifier,
    TrustPolicyWithOptions,
    BlockLowTrustPolicy,
    RequireAuthPolicy,
    parse_trust_level,
)

# Pipeline exports
from model_governance.pipelines import PipelineStage, PipelineResult, InputPipeline, OutputPipeline

# Input pipelines
from model_governance.pipelines.input import (
    SystemPromptPipeline,
    UserInputPipeline,
    ToolInputPipeline,
    AttachmentPipeline,
    Base64Pipeline,
)

# Output pipelines
from model_governance.pipelines.output import (
    SemanticCheckPipeline,
    LLMCheckPipeline,
    CompositeOutputPipeline,
)

# Policy exports
from model_governance.policies import (
    Policy,
    PolicyResult,
    PolicyAction,
    PolicyDecision,
    PolicyRegistry,
    ContentBlockingPolicy,
    PromptInjectionPolicy,
    MaliciousCodePolicy,
)

from model_governance.policies.content import (
    HTMLBlockingPolicy,
    JSONBlockingPolicy,
    CodeBlockPolicy,
)

from model_governance.policies.format import (
    JSONEnforcementPolicy,
    StructuredOutputPolicy,
    MaxLengthPolicy,
)

from model_governance.policies.enforcement import (
    EnforcementMechanism,
    BlockingEnforcer,
    StrictEnforcer,
    ReviewEnforcer,
    CompositeEnforcer,
    EnforcementDecision,
)

# Validator exports
from model_governance.validators import (
    validate_no_injection,
    validate_no_code_execution,
    validate_length,
    TopicGuard,
    SelfHarmGuard,
    HateSpeechGuard,
    ThreatsGuard,
)

# Checker exports
from model_governance.checkers import (
    EmbeddingSemanticChecker,
    ZaiLLMChecker,
)

# Utility exports
from model_governance.utils import (
    apply_policies,
    with_trust_level,
    async_pipeline,
    run_parallel_pipelines,
    run_with_timeout,
    retry_with_backoff,
)

# Main governance system class
class GovernanceSystem:
    """Main governance system for processing inputs and outputs.

    This class provides a high-level interface for using the governance
    system with all its components.

    Example:
        ```python
        system = GovernanceSystem()

        # Process input
        result = await system.process_input(
            source="user_input",
            content="Hello",
            trust_level="medium"
        )

        # Process output
        result = await system.process_output(
            content="Response here"
        )
        ```
    """

    def __init__(
        self,
        config: GovernanceConfig | None = None,
    ) -> None:
        """Initialize the governance system.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self._config = config or GovernanceConfig()
        self._policy_registry = PolicyRegistry()
        self._trust_classifier = TrustClassifier()

        # Input pipelines
        self._system_prompt_pipeline = SystemPromptPipeline()
        self._user_input_pipeline = UserInputPipeline(classifier=self._trust_classifier)
        self._tool_input_pipeline = ToolInputPipeline(classifier=self._trust_classifier)
        self._attachment_pipeline = AttachmentPipeline(classifier=self._trust_classifier)
        self._base64_pipeline = Base64Pipeline(classifier=self._trust_classifier)

        # Output pipeline - create default checkers
        from model_governance.pipelines.output.semantic_check import PatternBasedSemanticChecker
        from model_governance.pipelines.output.llm_check import MockLLMChecker

        self._semantic_checker = PatternBasedSemanticChecker()
        self._llm_checker = MockLLMChecker()
        self._output_pipeline = CompositeOutputPipeline(
            semantic_checker=self._semantic_checker,
            llm_checker=self._llm_checker,
            enable_parallel=self._config.checker.enable_parallel_checks,
        )

        # Default policies
        self._setup_default_policies()

    def _setup_default_policies(self) -> None:
        """Set up default policies for the governance system."""
        self._policy_registry.register(PromptInjectionPolicy())
        self._policy_registry.register(MaliciousCodePolicy())

        self._policy_registry.create_chain(
            "input_validation",
            ["prompt_injection", "malicious_code"],
        )

    async def process_input(
        self,
        source: str,
        content: str,
        trust_level: str | TrustLevel | None = None,
        **kwargs: object,
    ) -> PipelineResult:
        """Process input through the appropriate pipeline.

        Args:
            source: The input source type (system_prompt, user_input, tool_input, attachment, base64).
            content: The input content to process.
            trust_level: Optional trust level string or enum.
            **kwargs: Additional parameters specific to the input type.

        Returns:
            PipelineResult with processing outcome.
        """
        pipeline_map = {
            "system_prompt": self._system_prompt_pipeline,
            "system": self._system_prompt_pipeline,
            "user_input": self._user_input_pipeline,
            "user": self._user_input_pipeline,
            "tool_input": self._tool_input_pipeline,
            "tool": self._tool_input_pipeline,
            "attachment": self._attachment_pipeline,
            "base64": self._base64_pipeline,
        }

        pipeline = pipeline_map.get(source.lower())
        if pipeline is None:
            return PipelineResult(
                success=False,
                errors=[f"Unknown input source: {source}"],
                blocked=True,
                block_reason=f"Invalid input source: {source}",
            )

        return await pipeline.process(content, **kwargs)

    async def process_output(
        self,
        content: str,
        enforce_format: str | None = None,
    ) -> PipelineResult:
        """Process output through safety checks.

        Args:
            content: The output content to check.
            enforce_format: Optional format to enforce (json, xml, etc.).

        Returns:
            PipelineResult with safety check results.
        """
        result = await self._output_pipeline.process(content)

        if enforce_format and result.success:
            format_policy = JSONEnforcementPolicy() if enforce_format == "json" else None
            if format_policy:
                policy_result = await format_policy.evaluate(content, {})
                if not policy_result.allowed:
                    return PipelineResult(
                        success=False,
                        errors=[policy_result.reason],
                        blocked=True,
                        block_reason=policy_result.reason,
                    )

        return result

    def register_policy(self, policy: Policy) -> None:
        """Register a custom policy.

        Args:
            policy: The policy to register.
        """
        self._policy_registry.register(policy)

    def create_policy_chain(self, chain_name: str, policy_names: list[str]) -> None:
        """Create a chain of policies.

        Args:
            chain_name: Name for the chain.
            policy_names: List of policy names to include.
        """
        self._policy_registry.create_chain(chain_name, policy_names)

    @property
    def config(self) -> GovernanceConfig:
        """Get the current configuration."""
        return self._config

    @property
    def policy_registry(self) -> PolicyRegistry:
        """Get the policy registry."""
        return self._policy_registry


__all__ = [
    # Version
    "__version__",
    # Core
    "GovernanceSystem",
    "GovernanceConfig",
    "CheckerConfig",
    "BlockingConfig",
    "TrustLevelConfig",
    "load_config",
    # Exceptions
    "GovernanceError",
    "PipelineError",
    "PolicyViolationError",
    "TrustLevelError",
    "ValidationError",
    # Trust levels
    "TrustLevel",
    "TrustContext",
    "TrustClassifier",
    "TrustPolicyWithOptions",
    "BlockLowTrustPolicy",
    "RequireAuthPolicy",
    "parse_trust_level",
    # Pipelines
    "PipelineStage",
    "PipelineResult",
    "InputPipeline",
    "OutputPipeline",
    # Input pipelines
    "SystemPromptPipeline",
    "UserInputPipeline",
    "ToolInputPipeline",
    "AttachmentPipeline",
    "Base64Pipeline",
    # Output pipelines
    "SemanticCheckPipeline",
    "LLMCheckPipeline",
    "CompositeOutputPipeline",
    # Policies
    "Policy",
    "PolicyResult",
    "PolicyAction",
    "PolicyDecision",
    "PolicyRegistry",
    "ContentBlockingPolicy",
    "PromptInjectionPolicy",
    "MaliciousCodePolicy",
    "HTMLBlockingPolicy",
    "JSONBlockingPolicy",
    "CodeBlockPolicy",
    "JSONEnforcementPolicy",
    "StructuredOutputPolicy",
    "MaxLengthPolicy",
    "EnforcementMechanism",
    "BlockingEnforcer",
    "StrictEnforcer",
    "ReviewEnforcer",
    "CompositeEnforcer",
    "EnforcementDecision",
    # Validators
    "validate_no_injection",
    "validate_no_code_execution",
    "validate_length",
    "TopicGuard",
    "SelfHarmGuard",
    "HateSpeechGuard",
    "ThreatsGuard",
    # Checkers
    "EmbeddingSemanticChecker",
    "ZaiLLMChecker",
    # Utilities
    "apply_policies",
    "with_trust_level",
    "async_pipeline",
    "run_parallel_pipelines",
    "run_with_timeout",
    "retry_with_backoff",
]
