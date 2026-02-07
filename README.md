# Model Governance System

A comprehensive Python system for LLM safety and compliance with input/output processing pipelines, trust level classification, and policy enforcement.

## Features

- **Input Processing Pipelines**: Separate pipelines for different input sources
  - System prompt (no processing, passes through)
  - User input (full validation with trust classification)
  - Tool input (tool-specific validation)
  - Attachment (file type and size validation)
  - Base64 (decode validation and content inspection)

- **Output Safety Pipelines**: Multi-method safety checks for model outputs
  - Semantic-based safety checks
  - LLM-based content analysis
  - Composite pipeline with parallel execution

- **Trust Level Classification**: 5-tier hierarchy (UNTRUSTED, LOW, MEDIUM, HIGH, CRITICAL)
  - Configurable trust-based policies
  - Historical trust scoring
  - Source-based classification

- **Policy System**: Extensible policy framework
  - Content blocking policies (HTML, JSON, code blocks)
  - Format enforcement (structured JSON)
  - Prompt injection detection
  - Malicious code detection
  - Topic guards (self-harm, hate speech, threats)

- **Enforcement Mechanisms**: Multiple enforcement strategies
  - Blocking enforcer
  - Strict enforcer
  - Review enforcer
  - Composite enforcer

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

## Quick Start

```python
import asyncio
from model_governance import GovernanceSystem, TrustLevel

async def main():
    # Create a governance system
    system = GovernanceSystem()

    # Process user input
    result = await system.process_input(
        source="user_input",
        content="Hello, how are you?",
        historical_trust=0.85
    )

    print(f"Success: {result.success}")
    print(f"Trust Level: {result.trust_level}")
    print(f"Blocked: {result.blocked}")

    # Process model output
    result = await system.process_output(
        content="Here is the information you requested."
    )

    print(f"Output Safe: {result.success}")
    print(f"Blocked: {result.blocked}")

asyncio.run(main())
```

## Input Source Types

| Source Type | Description | Default Trust Level |
|-------------|-------------|-------------------|
| `system_prompt` | System instructions | CRITICAL |
| `user_input` | User messages | LOW - HIGH (based on history) |
| `tool_input` | Tool calls | MEDIUM |
| `attachment` | File uploads | LOW |
| `base64` | Encoded content | LOW |

## Trust Levels

| Level | Value | Description |
|-------|-------|-------------|
| UNTRUSTED | 0 | Unknown or malicious sources |
| LOW | 1 | Limited trust, requires scrutiny |
| MEDIUM | 2 | Moderately trusted sources |
| HIGH | 3 | Highly trusted sources |
| CRITICAL | 4 | System-level trust |

## Policy Examples

```python
from model_governance import (
    GovernanceSystem,
    PromptInjectionPolicy,
    HTMLBlockingPolicy,
    JSONEnforcementPolicy,
)

# Create system
system = GovernanceSystem()

# Register custom policies
system.register_policy(PromptInjectionPolicy())
system.register_policy(HTMLBlockingPolicy())

# Create policy chains
system.create_policy_chain("input_checks", ["prompt_injection"])
system.create_policy_chain("output_checks", ["html_blocking"])
```

## Testing

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run unit tests
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -v

# Run with coverage
pytest --cov=src/model_governance --cov-report=html
```

## Project Structure

```
governance/
├── src/model_governance/
│   ├── core/           # Core foundation classes
│   ├── pipelines/      # Input/output pipelines
│   ├── trust/          # Trust level system
│   ├── policies/       # Policy framework
│   ├── validators/     # Validation utilities
│   ├── checkers/       # Safety checkers
│   └── utils/          # Helper functions
├── tests/              # Test suite
├── pyproject.toml      # Project configuration
└── requirements.txt    # Dependencies
```

## License

MIT
