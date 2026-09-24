"""Read-only preflight for this workflow checkout; never installs dependencies."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys


def inspect_environment(root: Path) -> list[str]:
    issues = []
    if sys.version_info < (3, 11):
        issues.append('Python 3.11+ required')
    if importlib.util.find_spec('yaml') is None:
        issues.append('PyYAML is missing; install the documented dev dependencies')
    spec = importlib.util.find_spec('uads')
    expected = root.resolve() / 'src' / 'uads' / '__init__.py'
    if spec is None or spec.origin is None or Path(spec.origin).resolve() != expected:
        issues.append('uads editable install is missing or points to another checkout; '
                      'use the project venv: python -m pip install --no-deps -e .')
    try:
        result = subprocess.run(['git', '--version'], capture_output=True, timeout=10)
        if result.returncode:
            issues.append('Git is not usable')
    except (OSError, subprocess.SubprocessError):
        issues.append('Git is not available; Git-based evidence requires Git')
    for name in ('model_router.py', 'route_preflight.py', 'execution_contract_validate.py', 'delivery_evidence.py'):
        if not (root / 'tools' / name).is_file():
            issues.append('Missing workflow tool: ' + name)
    return issues


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    issues = inspect_environment(root)
    for issue in issues:
        print('FAIL: ' + issue)
    if not issues:
        print('Environment check passed: Python, checkout import, dependencies, Git, tools')
    return int(bool(issues))


if __name__ == '__main__':
    raise SystemExit(main())
