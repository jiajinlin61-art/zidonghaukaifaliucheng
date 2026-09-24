"""Resolve an execution profile to a concrete backend/model binding.

The router is deterministic. It does not execute a model; it selects an appropriate
role/profile/binding and emits a command hint after normal permission and workspace
checks.
"""
from __future__ import annotations

import argparse
from collections.abc import Collection
import json
from pathlib import Path
import sys
from typing import Any

import yaml

DEFAULT_CONFIG = (
    Path(__file__).resolve().parents[1]
    / "ai-development-workflow-v1"
    / "routing"
    / "MODEL_BINDINGS.yaml"
)

COMPLEXITY_RANK = {
    "TRIVIAL": 0,
    "SIMPLE": 1,
    "STANDARD": 2,
    "COMPLEX": 3,
    "CRITICAL": 4,
}

RISK_RANK = {
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 2,
    "CRITICAL": 3,
}

PROFILE_STRENGTH = {
    "planning-deep": 4,
    "coding-economy": 0,
    "coding-fast": 1,
    "visual-coding": 2,
    "coding-standard": 2,
    "coding-complex": 3,
    "coding-critical": 4,
    "debug-standard": 1,
    "debug-deep": 3,
    "review-standard": 2,
    "review-critical": 4,
}

PURPOSE_ROLE = {
    "planning": "planner",
    "execute": "worker",
    "debug": "debugger",
    "review": "reviewer",
}


def fail(message: str) -> None:
    raise ValueError(message)


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        fail("routing config must be a mapping")
    if value.get("schema_version") != "1.0":
        fail("unsupported routing schema_version")

    profiles = value.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        fail("routing config requires profiles")

    verification_policy = value.get("verification_policy", {})
    allowed = verification_policy.get(
        "auto_select_statuses",
        ["cli_probe_pass", "product_controller"],
    )
    if not isinstance(allowed, list) or not allowed or not all(isinstance(item, str) for item in allowed):
        fail("verification_policy.auto_select_statuses must be a non-empty string list")

    for name, profile in profiles.items():
        if not isinstance(profile, dict):
            fail(f"profile {name}: expected mapping")
        if not isinstance(profile.get("role"), str):
            fail(f"profile {name}: missing role")
        candidates = profile.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            fail(f"profile {name}: candidates must be non-empty")
        for candidate in candidates:
            if not isinstance(candidate, dict):
                fail(f"profile {name}: candidate must be mapping")
            for key in ("backend", "model", "effort", "verification"):
                if not isinstance(candidate.get(key), str) or not candidate[key].strip():
                    fail(f"profile {name}: candidate missing {key}")
    return value


def automatic_profile(
    *,
    purpose: str,
    complexity: str,
    risk: str,
    task_kind: str,
    failure_count: int,
    config: dict[str, Any],
) -> str:
    c = COMPLEXITY_RANK[complexity]
    r = RISK_RANK[risk]

    if purpose == "planning":
        profile = "planning-deep"
    elif purpose == "review":
        profile = (
            "review-critical"
            if r >= RISK_RANK["HIGH"] or c >= COMPLEXITY_RANK["CRITICAL"]
            else "review-standard"
        )
    elif purpose == "debug":
        profile = (
            "debug-deep"
            if r >= RISK_RANK["HIGH"]
            or c >= COMPLEXITY_RANK["COMPLEX"]
            or failure_count >= 2
            else "debug-standard"
        )
    elif purpose == "execute":
        if (
            task_kind == "visual"
            and c <= COMPLEXITY_RANK["STANDARD"]
            and r <= RISK_RANK["MEDIUM"]
        ):
            profile = "visual-coding"
        elif c == COMPLEXITY_RANK["TRIVIAL"] and r == RISK_RANK["LOW"]:
            profile = "coding-economy"
        elif c <= COMPLEXITY_RANK["SIMPLE"] and r == RISK_RANK["LOW"]:
            profile = "coding-fast"
        elif c <= COMPLEXITY_RANK["STANDARD"] and r <= RISK_RANK["MEDIUM"]:
            profile = "coding-standard"
        elif c <= COMPLEXITY_RANK["COMPLEX"] and r < RISK_RANK["CRITICAL"]:
            profile = "coding-complex"
        else:
            profile = "coding-critical"

        # failure_count is the number of materially identical failures already
        # recorded. The second retry (third total attempt) escalates after two
        # same-fingerprint failures.
        if failure_count >= 2:
            profile = config.get("escalation", {}).get(profile, profile)
    else:
        fail(f"unsupported purpose: {purpose}")

    if profile not in config["profiles"]:
        fail(f"routing config does not define selected profile: {profile}")
    return profile


def choose_profile(
    *,
    purpose: str,
    complexity: str,
    risk: str,
    task_kind: str,
    failure_count: int,
    override: str | None,
    override_reason: str | None,
    config: dict[str, Any],
) -> str:
    profile = automatic_profile(
        purpose=purpose,
        complexity=complexity,
        risk=risk,
        task_kind=task_kind,
        failure_count=failure_count,
        config=config,
    )
    if not override:
        return profile

    profiles = config["profiles"]
    if override not in profiles:
        fail(f"unknown profile override: {override}")
    if not isinstance(override_reason, str) or not override_reason.strip():
        fail("profile override requires a non-empty override reason")

    expected_role = PURPOSE_ROLE[purpose]
    actual_role = profiles[override].get("role")
    if actual_role != expected_role:
        fail(
            f"profile override role mismatch: {override} is {actual_role}, "
            f"expected {expected_role}"
        )

    if PROFILE_STRENGTH.get(override, -1) < PROFILE_STRENGTH.get(profile, -1):
        fail(
            f"profile override cannot downgrade required capability: "
            f"{profile} -> {override}"
        )
    return override


def normalize_exclusions(
    excluded_backends: Collection[str] | None,
    fallback_reason: str | None,
) -> list[str]:
    if not excluded_backends:
        return []
    if not isinstance(fallback_reason, str) or not fallback_reason.strip():
        fail("backend exclusion requires a non-empty fallback reason")
    exclusions: list[str] = []
    for backend in excluded_backends:
        if not isinstance(backend, str) or not backend.strip():
            fail("excluded backends must be non-empty strings")
        if backend not in exclusions:
            exclusions.append(backend)
    return exclusions


def choose_candidate(
    *,
    profile_name: str,
    config: dict[str, Any],
    worker_backend: str | None,
    excluded_backends: Collection[str] | None = None,
) -> dict[str, Any]:
    profile = config["profiles"][profile_name]
    allowed_verification = set(
        config.get("verification_policy", {}).get(
            "auto_select_statuses",
            ["cli_probe_pass", "product_controller"],
        )
    )
    candidates = [
        candidate
        for candidate in profile["candidates"]
        if candidate.get("enabled", True)
        and candidate.get("verification") in allowed_verification
    ]
    if not candidates:
        fail(f"profile {profile_name}: no enabled and verified candidate")

    if excluded_backends:
        exclusions = set(excluded_backends)
        compatible = [
            candidate for candidate in candidates if candidate.get("backend") not in exclusions
        ]
        if not compatible:
            fail(
                f"profile {profile_name}: runtime backend exclusions "
                f"{sorted(exclusions)} removed all enabled and verified candidates; "
                "no compatible route remains"
            )
        candidates = compatible

    if (
        profile.get("role") == "reviewer"
        and worker_backend
        and config.get("review_policy", {}).get("prefer_different_backend_from_worker", False)
    ):
        cross_backend = [candidate for candidate in candidates if candidate.get("backend") != worker_backend]
        if cross_backend:
            candidates = cross_backend + [
                candidate for candidate in candidates if candidate.get("backend") == worker_backend
            ]

    return dict(candidates[0])


def command_hint(candidate: dict[str, Any]) -> list[str] | None:
    backend = candidate["backend"]
    model = candidate["model"]
    effort = candidate["effort"]
    if backend == "codex":
        return [
            "codex",
            "exec",
            "-C",
            "<WORKSPACE>",
            "-m",
            model,
            "-c",
            f'model_reasoning_effort="{effort}"',
            "-",
        ]
    if backend == "claude-code":
        return [
            "claude",
            "-p",
            "--model",
            model,
            "--effort",
            effort,
            "--permission-mode",
            "auto",
            "<PROMPT>",
        ]
    return None


def resolve_route(
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
) -> dict[str, Any]:
    exclusions = normalize_exclusions(excluded_backends, fallback_reason)
    config = load_config(config_path)
    profile = choose_profile(
        purpose=purpose,
        complexity=complexity,
        risk=risk,
        task_kind=task_kind,
        failure_count=failure_count,
        override=override,
        override_reason=override_reason,
        config=config,
    )
    candidate = choose_candidate(
        profile_name=profile,
        config=config,
        worker_backend=worker_backend,
        excluded_backends=exclusions,
    )
    return {
        "purpose": purpose,
        "role": config["profiles"][profile]["role"],
        "profile": profile,
        "backend": candidate["backend"],
        "model": candidate["model"],
        "effort": candidate["effort"],
        "verification": candidate.get("verification", "unknown"),
        "override_reason": override_reason if override else None,
        "excluded_backends": exclusions,
        "fallback_reason": fallback_reason if exclusions else None,
        "command_hint": command_hint(candidate),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--purpose", choices=["planning", "execute", "debug", "review"], default="execute")
    parser.add_argument("--complexity", choices=list(COMPLEXITY_RANK), default="STANDARD")
    parser.add_argument("--risk", choices=list(RISK_RANK), default="MEDIUM")
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
    args = parser.parse_args()

    if args.failure_count < 0:
        parser.error("--failure-count must be >= 0")

    try:
        route = resolve_route(
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
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"model routing failed: {error}", file=sys.stderr)
        return 1

    print(json.dumps(route, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
