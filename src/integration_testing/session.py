"""Drive a Claude Agent SDK session and capture its output.

This is the only module that touches ``claude-agent-sdk``. It imports the SDK
lazily so the rest of the harness (models, loader, matchers) can be used and
unit-tested without the SDK installed. The SDK authenticates exactly like the
local Claude Code CLI -- there is no API key to pass.
"""

import asyncio
import dataclasses
from typing import Any

from integration_testing.models import SessionConfig
from integration_testing.recorder import SessionRecorder

# Field name -> SessionConfig attribute. The SDK option names match 1:1.
_OPTION_FIELDS = (
    "model",
    "cwd",
    "setting_sources",
    "mcp_servers",
    "allowed_tools",
    "disallowed_tools",
    "permission_mode",
    "max_turns",
    "system_prompt",
    "add_dirs",
    "env",
)


def _import_sdk():  # type: ignore[no-untyped-def]
    try:
        import claude_agent_sdk as sdk
    except ImportError as exc:
        raise RuntimeError(
            "claude-agent-sdk is not installed. Install with:\n"
            "    pip install claude-agent-sdk\n"
            "and ensure the Claude Code CLI is installed and logged in "
            "(the harness reuses those credentials)."
        ) from exc
    return sdk


def _build_options(sdk: Any, config: SessionConfig, recorder: SessionRecorder) -> Any:
    """Construct ClaudeAgentOptions, tolerating SDK versions missing newer fields."""
    options_cls = sdk.ClaudeAgentOptions
    kwargs: dict[str, Any] = {}
    for name in _OPTION_FIELDS:
        value = getattr(config, name)
        if value is not None:
            kwargs[name] = value

    if dataclasses.is_dataclass(options_cls):
        valid = {f.name for f in dataclasses.fields(options_cls)}
        unsupported = [k for k in kwargs if k not in valid]
        for key in unsupported:
            recorder.note(f"SDK does not support option '{key}'; ignored")
            kwargs.pop(key)

    return options_cls(**kwargs)


async def run_session(
    prompt: str, config: SessionConfig, timeout: float | None = None
) -> SessionRecorder:
    """Run a single agent session for ``prompt`` and return the populated recorder.

    Any SDK or process error (including a timeout) is captured on the recorder
    rather than raised, so a failing session still produces a printable result.
    """
    sdk = _import_sdk()
    recorder = SessionRecorder()
    try:
        options = _build_options(sdk, config, recorder)
    except Exception as exc:  # noqa: BLE001 - surface config errors as test failures
        recorder.mark_error(f"failed to build options: {type(exc).__name__}: {exc}")
        return recorder

    async def _consume() -> None:
        async for message in sdk.query(prompt=prompt, options=options):
            recorder.record(message)

    try:
        if timeout is not None:
            async with asyncio.timeout(timeout):
                await _consume()
        else:
            await _consume()
    except TimeoutError:
        recorder.mark_error(f"session timed out after {timeout}s")
    except Exception as exc:  # noqa: BLE001 - record SDK/process errors for reporting
        recorder.mark_error(f"{type(exc).__name__}: {exc}")

    return recorder
