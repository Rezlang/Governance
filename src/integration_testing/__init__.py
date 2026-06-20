"""Integration testing harness for MCP tools and Claude skills.

This package spins up real Claude agent sessions using the **Claude Agent SDK**
(``claude-agent-sdk``) and asserts on which MCP tools and skills the agent
activates. It deliberately uses the Agent SDK -- not the Anthropic Messages /
"claude.ai" API -- so it runs against the same underlying Claude credentials the
local Claude Code CLI already uses. There is nothing to configure for auth: if
``claude`` works in your shell, the harness works.

Two capabilities are supported, declared in YAML (see :mod:`.models`):

* **Activation** -- given a trigger phrase, is the correct skill/tool used?
* **Chain activation** -- given skill/tool *A* is activated (automatically via a
  prompt, or manually by directing the agent), is the expected *set* of other
  skills/tools also activated? Argument matching is optional.

All raw agent output is recorded and printed for failing tests.

Example:
    ```python
    import asyncio
    from integration_testing import load_suite, run_suite, report

    suite = load_suite("src/integration_testing/examples/tools.test.yaml")
    results = asyncio.run(run_suite(suite))
    exit_code = report(results)
    ```
"""

from integration_testing.loader import load_suite, load_suites
from integration_testing.models import (
    ChainTrigger,
    ExpectedActivation,
    SessionConfig,
    TestCase,
    TestSuite,
)
from integration_testing.recorder import RecordedToolUse, SessionRecorder
from integration_testing.reporter import report
from integration_testing.results import ActivationCheck, TestResult
from integration_testing.runner import run_suite, run_suites, run_test
from integration_testing.session import run_session

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # YAML spec models
    "TestSuite",
    "TestCase",
    "SessionConfig",
    "ChainTrigger",
    "ExpectedActivation",
    # Loading
    "load_suite",
    "load_suites",
    # Execution
    "run_session",
    "run_test",
    "run_suite",
    "run_suites",
    # Recording / results
    "SessionRecorder",
    "RecordedToolUse",
    "TestResult",
    "ActivationCheck",
    # Reporting
    "report",
]
