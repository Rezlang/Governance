"""Pydantic models defining the test YAML structure.

A test suite is a single YAML document with optional ``defaults`` (a
:class:`SessionConfig`) and a list of ``tests`` (:class:`TestCase`). Each test is
either an ``activation`` test (a trigger phrase -> expected tool/skill) or a
``chain`` test (activation of a seed tool/skill -> expected downstream set).

See ``examples/tools.test.yaml`` and ``examples/skills.test.yaml`` for fully
worked, commented documents.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TestType = Literal["activation", "chain"]
TestKind = Literal["tool", "skill"]
MatchMode = Literal["auto", "exact", "loose", "glob"]
TriggerMode = Literal["auto", "manual"]


class SessionConfig(BaseModel):
    """Options for spinning up a Claude Agent SDK session.

    Every field is optional. Suite-level ``defaults`` provide a baseline and a
    per-test ``session`` block overrides individual fields (see :meth:`merge`).
    Unset fields fall back to the SDK's own defaults.
    """

    model_config = ConfigDict(extra="forbid")

    model: str | None = Field(
        default=None,
        description="Claude model id, e.g. 'claude-opus-4-8'. Omit to use the SDK default.",
    )
    cwd: str | None = Field(
        default=None,
        description="Working directory for the agent. Skills/MCP are resolved relative to this.",
    )
    setting_sources: list[str] | None = Field(
        default=None,
        description=(
            "Which Claude settings to load: any of 'user', 'project', 'local'. "
            "Must include the source that defines the skills/MCP servers under test "
            "(usually ['project'])."
        ),
    )
    mcp_servers: dict[str, dict[str, Any]] | str | None = Field(
        default=None,
        description="MCP server definitions (name -> config), or a path to an MCP config file.",
    )
    allowed_tools: list[str] | None = Field(
        default=None,
        description="Allow-list of tool names the agent may use (e.g. 'mcp__weather__forecast').",
    )
    disallowed_tools: list[str] | None = Field(
        default=None, description="Deny-list of tool names the agent may not use."
    )
    permission_mode: str | None = Field(
        default=None,
        description=(
            "One of 'default', 'acceptEdits', 'plan', 'bypassPermissions'. "
            "Use 'bypassPermissions' so tools actually fire without interactive prompts."
        ),
    )
    max_turns: int | None = Field(
        default=None, description="Maximum agent turns before the session is stopped."
    )
    system_prompt: str | None = Field(
        default=None, description="Override the agent system prompt."
    )
    add_dirs: list[str] | None = Field(
        default=None, description="Extra directories the agent may access."
    )
    env: dict[str, str] | None = Field(
        default=None, description="Extra environment variables for the agent process."
    )

    def merge(self, override: "SessionConfig | None") -> "SessionConfig":
        """Return a new config with non-None fields from ``override`` applied on top."""
        if override is None:
            return self.model_copy(deep=True)
        data = self.model_dump()
        for key, value in override.model_dump().items():
            if value is not None:
                data[key] = value
        return SessionConfig(**data)


class ExpectedActivation(BaseModel):
    """An expectation that a particular tool or skill was activated.

    Accepts a YAML shorthand: a bare string is coerced to ``{name: <string>}``.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        description="Tool or skill name. Supports glob patterns and bare-name matching."
    )
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional subset of arguments the invocation must include. "
        "String values may use glob patterns.",
    )
    match: MatchMode = Field(
        default="auto",
        description=(
            "How 'name' is matched: 'exact' (full tool name), 'loose' (bare name / "
            "skill name, ignoring the 'mcp__server__' prefix), 'glob', or 'auto' "
            "(glob if wildcards present, exact for 'mcp__' names, else loose)."
        ),
    )
    min_count: int = Field(
        default=1, ge=1, description="Minimum number of matching invocations required."
    )
    optional: bool = Field(
        default=False,
        description="If true, a missing activation does not fail the test (still reported).",
    )

    def describe(self) -> str:
        """Human-readable description for reports."""
        suffix = ""
        if self.arguments:
            suffix = f" with args {self.arguments}"
        if self.min_count > 1:
            suffix += f" (x{self.min_count})"
        if self.optional:
            suffix += " [optional]"
        return f"{self.name}{suffix}"


class ChainTrigger(BaseModel):
    """How the seed tool/skill *A* of a chain test is activated."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(description="The user prompt that drives the session.")
    mode: TriggerMode = Field(
        default="auto",
        description=(
            "'auto' sends the prompt as-is and lets the model decide. "
            "'manual' prepends an explicit directive forcing the seed to run first."
        ),
    )
    seed: str | None = Field(
        default=None,
        description="The seed tool/skill A. Required for 'manual' mode; "
        "if set, the harness also asserts A actually activated.",
    )
    seed_kind: TestKind = Field(
        default="tool", description="Whether the seed is a 'tool' or a 'skill'."
    )

    @model_validator(mode="after")
    def _require_seed_for_manual(self) -> "ChainTrigger":
        if self.mode == "manual" and not self.seed:
            raise ValueError("chain trigger with mode 'manual' requires a 'seed'")
        return self


class TestCase(BaseModel):
    """A single activation or chain test."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Unique test name.")
    description: str | None = None
    type: TestType = Field(default="activation", description="'activation' or 'chain'.")
    kind: TestKind = Field(
        default="tool",
        description="Primary subject under test ('tool' or 'skill'); affects defaults/reporting.",
    )

    # activation tests
    prompt: str | None = Field(
        default=None, description="Trigger phrase (required for 'activation' tests)."
    )
    # chain tests
    trigger: ChainTrigger | None = Field(
        default=None, description="Seed activation spec (required for 'chain' tests)."
    )

    expect_activated: list[ExpectedActivation] = Field(
        default_factory=list,
        description="Tools/skills that must be activated.",
    )
    expect_not_activated: list[str] = Field(
        default_factory=list,
        description="Tools/skills that must NOT be activated (names support globs).",
    )

    timeout: float | None = Field(
        default=None, description="Per-test timeout in seconds for the agent session."
    )
    session: SessionConfig | None = Field(
        default=None, description="Per-test overrides of the suite defaults."
    )

    @field_validator("expect_activated", mode="before")
    @classmethod
    def _coerce_shorthand(cls, value: Any) -> Any:
        """Allow each entry to be a bare string instead of a mapping."""
        if not isinstance(value, list):
            return value
        return [{"name": item} if isinstance(item, str) else item for item in value]

    @model_validator(mode="after")
    def _validate_shape(self) -> "TestCase":
        if self.type == "activation" and not self.prompt:
            raise ValueError(f"activation test '{self.name}' requires a 'prompt'")
        if self.type == "chain" and self.trigger is None:
            raise ValueError(f"chain test '{self.name}' requires a 'trigger'")
        if not self.expect_activated and not self.expect_not_activated:
            raise ValueError(
                f"test '{self.name}' must specify 'expect_activated' and/or 'expect_not_activated'"
            )
        return self


class TestSuite(BaseModel):
    """A collection of tests plus shared session defaults."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Suite name.")
    description: str | None = None
    defaults: SessionConfig = Field(
        default_factory=SessionConfig, description="Baseline session config for every test."
    )
    tests: list[TestCase] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_names(self) -> "TestSuite":
        seen: set[str] = set()
        for test in self.tests:
            if test.name in seen:
                raise ValueError(f"duplicate test name in suite '{self.name}': {test.name}")
            seen.add(test.name)
        return self
