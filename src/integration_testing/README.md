# Integration Testing Harness

A YAML-driven harness for testing **MCP tools** and **Claude skills** by spinning
up real Claude agent sessions with the [Claude Agent SDK](https://pypi.org/project/claude-agent-sdk/)
(`claude-agent-sdk`).

It deliberately uses the Agent SDK, **not** the Anthropic Messages / "claude.ai"
API. The SDK drives the same Claude Code runtime your terminal uses and reuses
its credentials — so there is **nothing to configure for auth**. If `claude`
works in your shell, the harness works.

## What it tests

- **Activation** — given a trigger phrase, is the right skill/tool activated
  (and are the wrong ones left alone)?
- **Chain activation** — given skill/tool *A* is activated (automatically by a
  prompt, or manually by directing the agent), is the expected *set* of other
  skills/tools also activated? Argument matching is optional.

Every session's full output is recorded; for any failing test the complete
transcript and the raw SDK message stream are printed.

## Install

```bash
pip install -e ".[integration-testing]"   # installs claude-agent-sdk + pyyaml
```

Also ensure the Claude Code CLI is installed and you are logged in.

## Run

```bash
# A single suite
python -m integration_testing src/integration_testing/examples/tools.test.yaml

# A directory (all *.test.yaml are discovered)
python -m integration_testing src/integration_testing/examples/

# Filter by test name, machine-readable output, verbose transcripts
python -m integration_testing examples/ -k weather
python -m integration_testing examples/ --json
python -m integration_testing examples/ -v
```

Exit code is `0` when all tests pass, `1` on failure, `2` when nothing matched.

You can also drive it from Python:

```python
import asyncio
from integration_testing import load_suite, run_suite, report

suite = load_suite("src/integration_testing/examples/tools.test.yaml")
results = asyncio.run(run_suite(suite))
raise SystemExit(report(results))
```

## YAML structure

A suite is one YAML document:

```yaml
name: My suite
description: optional
defaults:            # SessionConfig applied to every test (each test may override)
  model: claude-opus-4-8        # optional; omit for SDK default
  cwd: .
  setting_sources: [project]    # load project .claude/ (skills + MCP). Required for skills.
  permission_mode: bypassPermissions   # so tools fire without prompts
  max_turns: 8
  mcp_servers:                  # optional; or rely on setting_sources
    weather: { command: npx, args: ["-y", "@example/weather-mcp"] }
  allowed_tools: [...]          # optional allow-list
  disallowed_tools: [...]       # optional deny-list
  system_prompt: null           # optional override
tests:
  - ...
```

### Activation test

```yaml
- name: weather-activation
  type: activation        # default
  kind: tool              # tool | skill (affects reporting/defaults)
  prompt: What's the weather in Paris?
  timeout: 120            # optional, seconds
  expect_activated:
    - get_forecast                      # shorthand (loose name match)
    - name: mcp__weather__get_forecast  # full form
      match: exact                      # auto | exact | loose | glob
      arguments: { location: "*Paris*" }# optional subset match; strings allow globs
      min_count: 1                      # optional
      optional: false                   # optional
  expect_not_activated:
    - mcp__db__*          # names support globs
  session:                # optional per-test override of defaults
    permission_mode: default
```

### Chain test

```yaml
- name: search-then-save
  type: chain
  kind: tool
  trigger:
    mode: auto            # auto: send prompt as-is | manual: force the seed first
    seed: mcp__search__web_search   # required for manual; if set, A is asserted to fire
    seed_kind: tool       # tool | skill
    prompt: Research MCP and save a summary to my notes.
  expect_activated:
    - mcp__notes__save
  expect_not_activated: []
```

### Name matching

| Expectation              | Matches                                           |
| ------------------------ | ------------------------------------------------- |
| `mcp__weather__forecast` | exact full tool name                              |
| `forecast`               | loose — the bare name, ignoring `mcp__server__`   |
| `code-review`            | a `Skill` invocation whose skill name is that     |
| `mcp__weather__*`        | glob                                              |

`auto` mode (the default) picks: glob if the pattern has wildcards, exact for
`mcp__` names, otherwise loose.

## Module map

| Module        | Responsibility                                            |
| ------------- | --------------------------------------------------------- |
| `models.py`   | Pydantic models defining the YAML schema                  |
| `loader.py`   | Load/validate `*.test.yaml` files                         |
| `session.py`  | The only module that imports `claude-agent-sdk`           |
| `recorder.py` | Normalize the SDK message stream (tools, skills, output)  |
| `matchers.py` | Name / argument matching logic                            |
| `runner.py`   | Build prompts, run sessions, evaluate expectations        |
| `reporter.py` | Console + JSON reporting (dumps transcripts on failure)   |
| `cli.py`      | `python -m integration_testing` entry point               |
