"""Captures and normalizes the message stream from a Claude Agent SDK session.

The recorder duck-types the SDK message/block objects by class name and attribute
presence, so importing this module never requires ``claude-agent-sdk`` to be
installed. It keeps three views of every session:

* :attr:`tool_uses` -- normalized :class:`RecordedToolUse` entries used for matching.
* :attr:`transcript` -- a readable, ordered rendering for humans.
* :attr:`raw_messages` -- the literal ``repr()`` of each SDK message, so failing
  tests can print exactly what the agent emitted.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RecordedToolUse:
    """A single tool or skill invocation observed in the session."""

    name: str
    kind: str  # "tool" or "skill"
    input: dict[str, Any] = field(default_factory=dict)
    server: str | None = None
    skill_name: str | None = None
    tool_use_id: str | None = None
    is_error: bool = False

    def label(self) -> str:
        if self.kind == "skill" and self.skill_name:
            return f"skill:{self.skill_name}"
        return self.name


# Keys we look at to recover a skill name from a Skill tool invocation.
_SKILL_NAME_KEYS = ("skill", "name", "command", "skill_name")


class SessionRecorder:
    """Accumulates normalized state from SDK messages."""

    def __init__(self) -> None:
        self.tool_uses: list[RecordedToolUse] = []
        self.raw_messages: list[str] = []
        self._lines: list[str] = []
        self.error: str | None = None
        self.duration_ms: float | None = None
        self.cost_usd: float | None = None
        self.num_turns: int | None = None
        self.session_id: str | None = None
        self.result_is_error: bool = False
        self.notes: list[str] = []

    # -- public API ---------------------------------------------------------

    @property
    def transcript(self) -> str:
        return "\n".join(self._lines)

    def mark_error(self, message: str) -> None:
        self.error = message
        self._lines.append(f"!! ERROR: {message}")

    def note(self, message: str) -> None:
        self.notes.append(message)
        self._lines.append(f"-- note: {message}")

    def record(self, message: Any) -> None:
        """Record one SDK message, normalizing it for later inspection."""
        self.raw_messages.append(repr(message))
        cls = type(message).__name__

        if cls == "AssistantMessage":
            self._record_assistant(message)
        elif cls == "UserMessage":
            self._record_user(message)
        elif cls == "SystemMessage":
            self._record_system(message)
        elif cls == "ResultMessage":
            self._record_result(message)
        else:
            self._lines.append(f"[{cls}]")

    # -- internals ----------------------------------------------------------

    def _record_assistant(self, message: Any) -> None:
        for block in getattr(message, "content", []) or []:
            btype = type(block).__name__
            if btype == "TextBlock":
                text = getattr(block, "text", "")
                if text.strip():
                    self._lines.append(f"assistant: {text.strip()}")
            elif btype == "ThinkingBlock":
                thinking = getattr(block, "thinking", "")
                if thinking.strip():
                    self._lines.append(f"assistant[thinking]: {thinking.strip()}")
            elif btype == "ToolUseBlock":
                self._record_tool_use(block)
            else:
                self._lines.append(f"assistant[{btype}]")

    def _record_tool_use(self, block: Any) -> None:
        name = getattr(block, "name", "") or ""
        tool_input = getattr(block, "input", {}) or {}
        if not isinstance(tool_input, dict):
            tool_input = {"_value": tool_input}
        tool_use_id = getattr(block, "id", None)

        if name == "Skill":
            skill_name = self._extract_skill_name(tool_input)
            use = RecordedToolUse(
                name=name,
                kind="skill",
                input=tool_input,
                skill_name=skill_name,
                tool_use_id=tool_use_id,
            )
            self._lines.append(f"tool_use: Skill -> {skill_name} {tool_input}")
        else:
            server = name.split("__")[1] if name.startswith("mcp__") and "__" in name else None
            use = RecordedToolUse(
                name=name,
                kind="tool",
                input=tool_input,
                server=server,
                tool_use_id=tool_use_id,
            )
            self._lines.append(f"tool_use: {name} {tool_input}")
        self.tool_uses.append(use)

    @staticmethod
    def _extract_skill_name(tool_input: dict[str, Any]) -> str | None:
        for key in _SKILL_NAME_KEYS:
            value = tool_input.get(key)
            if isinstance(value, str) and value:
                # Slash-command style "/foo args" -> "foo".
                token = value.strip().lstrip("/").split()[0] if value.strip() else ""
                return token or value
        return None

    def _record_user(self, message: Any) -> None:
        content = getattr(message, "content", None)
        if isinstance(content, str):
            if content.strip():
                self._lines.append(f"user: {content.strip()}")
            return
        for block in content or []:
            btype = type(block).__name__
            if btype == "ToolResultBlock":
                tool_use_id = getattr(block, "tool_use_id", None)
                is_error = bool(getattr(block, "is_error", False))
                if is_error:
                    self._mark_tool_error(tool_use_id)
                preview = self._preview(getattr(block, "content", None))
                flag = " [error]" if is_error else ""
                self._lines.append(f"tool_result{flag} ({tool_use_id}): {preview}")

    def _mark_tool_error(self, tool_use_id: str | None) -> None:
        if tool_use_id is None:
            return
        for use in self.tool_uses:
            if use.tool_use_id == tool_use_id:
                use.is_error = True

    def _record_system(self, message: Any) -> None:
        subtype = getattr(message, "subtype", "") or ""
        self._lines.append(f"[system:{subtype}]")

    def _record_result(self, message: Any) -> None:
        self.duration_ms = getattr(message, "duration_ms", None)
        self.cost_usd = getattr(message, "total_cost_usd", None)
        self.num_turns = getattr(message, "num_turns", None)
        self.session_id = getattr(message, "session_id", None)
        self.result_is_error = bool(getattr(message, "is_error", False))
        subtype = getattr(message, "subtype", "") or ""
        if self.result_is_error and self.error is None:
            result_text = getattr(message, "result", None)
            self.mark_error(f"agent reported error result (subtype={subtype}): {result_text}")
        self._lines.append(
            f"[result subtype={subtype} turns={self.num_turns} cost=${self.cost_usd}]"
        )

    @staticmethod
    def _preview(content: Any, limit: int = 200) -> str:
        text = content if isinstance(content, str) else repr(content)
        text = text.replace("\n", " ")
        return text if len(text) <= limit else text[:limit] + "..."
