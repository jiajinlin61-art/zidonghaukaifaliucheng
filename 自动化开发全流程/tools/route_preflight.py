"""Preflight a selected model route against the current local environment.

This checks local executability and probe-context freshness:
- backend executable exists;
- CLI version still matches the version used for the recorded model probes;
- a sanitized, non-secret local config fingerprint still matches;
- the selected model id is in the backend's recorded probed_models list.

It does not call the model/provider. A successful preflight means the recorded probe is
still compatible with the current local CLI/config context, not that a new remote model
request succeeded.
"""
from __future__ import annotations

import argparse
from collections.abc import Collection
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.model_router import DEFAULT_CONFIG, load_config, resolve_route

SENSITIVE_KEY_RE = re.compile(r"(token|secret|password|api[_-]?key|auth)", re.IGNORECASE)


def fail(message: str) -> None:
    raise ValueError(message)


def scrub_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, child in value.items():
            if SENSITIVE_KEY_RE.search(str(key)):
                continue
            result[str(key)] = scrub_sensitive(child)
        return result
    if isinstance(value, list):
        return [scrub_sensitive(item) for item in value]
    return value


def canonical_hash(value: Any) -> str:
    payload = json.dumps(
        scrub_sensitive(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def load_backend_config(backend: str, home: Path | None = None) -> Any:
    root = home or Path.home()
    if backend == "codex":
        path = root / ".codex" / "config.toml"
        with path.open("rb") as stream:
            return tomllib.load(stream)
    if backend == "claude-code":
        path = root / ".claude" / "settings.json"
        return json.loads(path.read_text(encoding="utf-8"))
    fail(f"backend {backend}: no local config fingerprint adapter")


def config_fingerprint(backend: str, home: Path | None = None) -> str:
    return canonical_hash(load_backend_config(backend, home))


def run_version(executable: str) -> str:
    resolved = shutil.which(executable)
    if not resolved:
        fail(f"backend executable not found: {executable}")
    completed = subprocess.run(
        [resolved, "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    output = (completed.stdout + "\n" + completed.stderr).strip()
    if completed.returncode != 0:
        fail(f"{executable} --version failed with exit {completed.returncode}: {output}")
    if not output:
        fail(f"{executable} --version returned no output")
    return output


def locate_candidate(config: dict[str, Any], route: dict[str, Any]) -> dict[str, Any]:
    profile = config["profiles"][route["profile"]]
    for candidate in profile["candidates"]:
        if candidate.get("backend") == route["backend"] and candidate.get("model") == route["model"]:
            return candidate
    fail("selected route candidate not found in routing config")


def validate_probe_freshness(config: dict[str, Any], preflight: dict[str, Any]) -> None:
    verified_at = preflight.get("verified_at")
    if not isinstance(verified_at, str) or not verified_at.strip():
        fail("probe record missing verified_at")
    max_age_days = config.get("verification_policy", {}).get("max_probe_age_days")
    if isinstance(max_age_days, bool) or not isinstance(max_age_days, int) or max_age_days < 1:
        fail("verification_policy.max_probe_age_days must be a positive integer")
    try:
        verified = datetime.fromisoformat(verified_at)
    except ValueError as error:
        raise ValueError(f"invalid probe verified_at: {verified_at!r}") from error
    if verified.tzinfo is None:
        verified = verified.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    age_days = (now - verified.astimezone(timezone.utc)).total_seconds() / 86400
    if age_days < -1:
        fail("probe verified_at is unexpectedly in the future")
    if age_days > max_age_days:
        fail(
            f"probe record expired: age={age_days:.1f} days, "
            f"max={max_age_days} days; run a real model probe before automatic execution"
        )


def preflight_route(
    *,
    config_path: Path = DEFAULT_CONFIG,
    purpose: str = "execute",
    complexity: str = "STANDARD",
    risk: str = "MEDIUM",
    task_kind: str = "general",
    failure_count: int = 0,
    override: str | None = None,
    override_reason: str | None = None,
    worker_backend: str | None = None,
    excluded_backends: Collection[str] | None = None,
    fallback_reason: str | None = None,
    home: Path | None = None,
) -> dict[str, Any]:
    config = load_config(config_path)
    route = resolve_route(
        config_path=config_path,
        purpose=purpose,
        complexity=complexity,
        risk=risk,
        task_kind=task_kind,
        failure_count=failure_count,
        override=override,
        override_reason=override_reason,
        worker_backend=worker_backend,
        excluded_backends=excluded_backends,
        fallback_reason=fallback_reason,
    )
    candidate = locate_candidate(config, route)
    backend_name = route["backend"]
    if backend_name == "controller":
        return {
            "status": "external-controller",
            "route": route,
            "local_preflight": "not-applicable",
        }

    backends = config.get("backends", {})
    backend = backends.get(backend_name)
    if not isinstance(backend, dict):
        fail(f"backend configuration missing: {backend_name}")
    preflight = backend.get("preflight")
    if not isinstance(preflight, dict):
        fail(f"backend {backend_name}: missing preflight probe context")
    validate_probe_freshness(config, preflight)

    if candidate.get("verification") != "cli_probe_pass":
        fail(
            f"candidate {route['model']}: verification is "
            f"{candidate.get('verification')!r}, expected cli_probe_pass"
        )
    probed_models = preflight.get("probed_models")
    if not isinstance(probed_models, list) or route["model"] not in probed_models:
        fail(f"candidate {route['model']}: not present in current probed_models")

    executable = backend.get("executable")
    if not isinstance(executable, str) or not executable:
        fail(f"backend {backend_name}: executable missing")
    version_output = run_version(executable)
    version_contains = preflight.get("version_contains")
    if not isinstance(version_contains, str) or version_contains not in version_output:
        fail(
            f"backend {backend_name}: CLI version changed; "
            f"expected output containing {version_contains!r}"
        )

    expected_fingerprint = preflight.get("config_fingerprint")
    if not isinstance(expected_fingerprint, str) or not expected_fingerprint:
        fail(f"backend {backend_name}: config_fingerprint missing")
    actual_fingerprint = config_fingerprint(backend_name, home)
    if actual_fingerprint != expected_fingerprint:
        fail(
            f"backend {backend_name}: local config fingerprint changed; "
            "re-run a real model probe before automatic execution"
        )

    return {
        "status": "pass",
        "route": route,
        "backend_version_check": "pass",
        "config_fingerprint_check": "pass",
        "model_probe_record_check": "pass",
        "probe_freshness_check": "pass",
        "probe_verified_at": preflight.get("verified_at"),
        "probe_max_age_days": config.get("verification_policy", {}).get("max_probe_age_days"),
        "note": "local preflight only; no new remote model request was made",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--purpose", choices=["planning", "execute", "debug", "review"], default="execute")
    parser.add_argument(
        "--complexity",
        choices=["TRIVIAL", "SIMPLE", "STANDARD", "COMPLEX", "CRITICAL"],
        default="STANDARD",
    )
    parser.add_argument("--risk", choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"], default="MEDIUM")
    parser.add_argument("--task-kind", choices=["general", "mechanical", "visual"], default="general")
    parser.add_argument("--failure-count", type=int, default=0)
    parser.add_argument("--profile", dest="override")
    parser.add_argument("--override-reason")
    parser.add_argument("--worker-backend", choices=["codex", "claude-code"])
    parser.add_argument(
        "--exclude-backend",
        action="append",
        help="backend known unavailable at runtime; repeatable",
    )
    parser.add_argument("--fallback-reason")
    parser.add_argument(
        "--print-config-fingerprint",
        choices=["codex", "claude-code"],
        help="print only the sanitized current config fingerprint and exit",
    )
    args = parser.parse_args()

    try:
        if args.print_config_fingerprint:
            print(config_fingerprint(args.print_config_fingerprint))
            return 0
        result = preflight_route(
            config_path=args.config,
            purpose=args.purpose,
            complexity=args.complexity,
            risk=args.risk,
            task_kind=args.task_kind,
            failure_count=args.failure_count,
            override=args.override,
            override_reason=args.override_reason,
            worker_backend=args.worker_backend,
            excluded_backends=args.exclude_backend,
            fallback_reason=args.fallback_reason,
        )
    except (OSError, ValueError, subprocess.SubprocessError, json.JSONDecodeError, tomllib.TOMLDecodeError, yaml.YAMLError) as error:
        print(f"route preflight failed: {error}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
