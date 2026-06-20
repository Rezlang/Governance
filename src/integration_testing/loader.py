"""Load test suites from YAML files."""

from pathlib import Path

from integration_testing.models import TestSuite


def _require_yaml():  # type: ignore[no-untyped-def]
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - exercised only without pyyaml
        raise RuntimeError(
            "PyYAML is required to load test suites. Install with: pip install pyyaml"
        ) from exc
    return yaml


def load_suite(path: str | Path) -> TestSuite:
    """Parse and validate a single ``*.test.yaml`` file into a :class:`TestSuite`."""
    yaml = _require_yaml()
    file_path = Path(path)
    with file_path.open() as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{file_path}: expected a YAML mapping at the top level")
    data.setdefault("name", file_path.stem)
    return TestSuite.model_validate(data)


def discover(paths: list[str | Path], pattern: str = "*.test.yaml") -> list[Path]:
    """Expand a list of files/directories into concrete suite file paths."""
    found: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            found.extend(sorted(path.rglob(pattern)))
        else:
            found.append(path)
    return found


def load_suites(paths: list[str | Path], pattern: str = "*.test.yaml") -> list[TestSuite]:
    """Load every suite under the given files/directories."""
    return [load_suite(path) for path in discover(paths, pattern)]
