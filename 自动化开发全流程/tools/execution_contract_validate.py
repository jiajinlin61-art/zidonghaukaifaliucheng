"""Validate delegated execution request/result contracts.

Template mode validates reusable contract shape and allows placeholders.
Actual mode rejects placeholders and enforces evidence, scope, identity, validation
coverage, reviewer independence, and failure semantics.

This validator does not execute commands, inspect Git objects, or decide project-level
DONE. Integrators must still verify the real diff/commit and rerun required checks.
"""
from __future__ import annotations

import argparse
from fnmatch import fnmatchcase
from pathlib import Path, PureWindowsPath
import re
import sys
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.model_router import resolve_route

SCHEMA_VERSION = "1.3"
REQUEST_PURPOSES = {"execute"}
RESULT_STATUSES = {"READY_FOR_REVIEW", "REVIEW_PASSED", "FAILED", "NEEDS_HUMAN"}
WORKER_STATUSES = {"COMPLETED", "FAILED", "NEEDS_HUMAN"}
REVIEW_STATUSES = {"PENDING", "PASS", "FAIL", "NEEDS_HUMAN"}
REVIEWER_TYPES = {"model", "human"}
WORKER_EXECUTION_MODES = {"delegated", "controller_override"}
VERIFICATION_RESULTS = {"PASS", "FAIL", "NOT_RUN"}
VERIFICATION_MODES = {"commands", "semantic", "mixed"}
CHECK_KINDS = {"command", "semantic"}
BASELINE_KINDS = {"git", "no-git"}
PLACEHOLDER_RE = re.compile(r"<[^>\r\n]+>")
PLACEHOLDER_TOKENS = {"TBD", "TODO", "__PLACEHOLDER__", "REPLACE_ME"}


def fail(message: str) -> None:
    raise ValueError(message)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        fail(f"{path}: expected a mapping")
    return value


def nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(f"{label}: expected a non-empty string")
    return value.strip()


def positive_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        fail(f"{label}: expected a positive integer")
    return value


def nonnegative_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        fail(f"{label}: expected a non-negative integer")
    return value


def string_list(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list):
        fail(f"{label}: expected a list")
    if not allow_empty and not value:
        fail(f"{label}: must not be empty")
    result: list[str] = []
    for index, item in enumerate(value):
        result.append(nonempty_string(item, f"{label}[{index}]"))
    return result


def reject_placeholders(value: Any, label: str = "document") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            reject_placeholders(child, f"{label}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            reject_placeholders(child, f"{label}[{index}]")
        return
    if isinstance(value, str):
        stripped = value.strip()
        if PLACEHOLDER_RE.search(value) or stripped in PLACEHOLDER_TOKENS:
            fail(f"{label}: placeholder value is forbidden in actual mode: {value!r}")


def validate_identity(doc: dict[str, Any], label: str) -> None:
    if doc.get("schema_version") != SCHEMA_VERSION:
        fail(f"{label}: unsupported schema_version")
    nonempty_string(doc.get("task_id"), f"{label}.task_id")
    positive_integer(doc.get("task_revision"), f"{label}.task_revision")
    nonempty_string(doc.get("attempt_id"), f"{label}.attempt_id")


def validate_workspace(doc: dict[str, Any], label: str) -> None:
    workspace = doc.get("workspace")
    if not isinstance(workspace, dict):
        fail(f"{label}.workspace: expected mapping")
    nonempty_string(workspace.get("project_root"), f"{label}.workspace.project_root")
    baseline = workspace.get("baseline")
    if not isinstance(baseline, dict):
        fail(f"{label}.workspace.baseline: expected mapping")
    kind = baseline.get("kind")
    if kind not in BASELINE_KINDS:
        fail(f"{label}.workspace.baseline.kind: expected git or no-git")
    nonempty_string(baseline.get("ref"), f"{label}.workspace.baseline.ref")


def normalize_repo_path(value: str, label: str) -> str:
    item = nonempty_string(value, label).replace("\\", "/")
    posix = Path(item)
    windows = PureWindowsPath(item)
    if posix.is_absolute() or windows.is_absolute() or windows.drive:
        fail(f"{label}: absolute path is forbidden: {value}")
    if ".." in posix.parts or ".." in windows.parts:
        fail(f"{label}: parent traversal is forbidden: {value}")
    while item.startswith("./"):
        item = item[2:]
    if not item:
        fail(f"{label}: empty normalized path")
    return item


def validate_repo_relative_paths(value: Any, label: str) -> list[str]:
    paths = string_list(value, label)
    return [normalize_repo_path(item, f"{label}[{index}]") for index, item in enumerate(paths)]


def path_matches(path: str, pattern: str) -> bool:
    normalized_path = path.replace("\\", "/")
    normalized_pattern = pattern.replace("\\", "/")
    if fnmatchcase(normalized_path, normalized_pattern):
        return True
    if normalized_pattern.endswith("/**"):
        prefix = normalized_pattern[:-3].rstrip("/")
        return normalized_path == prefix or normalized_path.startswith(prefix + "/")
    return False


def validate_acceptance(doc: dict[str, Any]) -> set[str]:
    acceptance = doc.get("acceptance")
    if not isinstance(acceptance, list) or not acceptance:
        fail("request.acceptance: expected a non-empty list")
    ids: set[str] = set()
    for index, item in enumerate(acceptance):
        if not isinstance(item, dict):
            fail(f"request.acceptance[{index}]: expected mapping")
        acceptance_id = nonempty_string(item.get("id"), f"request.acceptance[{index}].id")
        if acceptance_id in ids:
            fail(f"request.acceptance: duplicate id {acceptance_id}")
        ids.add(acceptance_id)
        nonempty_string(item.get("criterion"), f"request.acceptance[{index}].criterion")
    return ids


def validate_required_checks(doc: dict[str, Any], acceptance_ids: set[str]) -> dict[str, dict[str, Any]]:
    validation = doc.get("validation")
    if not isinstance(validation, dict):
        fail("request.validation: expected mapping")
    mode = validation.get("mode")
    if mode not in VERIFICATION_MODES:
        fail("request.validation.mode: unsupported mode")
    checks = validation.get("required_checks")
    if not isinstance(checks, list) or not checks:
        fail("request.validation.required_checks: expected a non-empty list")

    by_id: dict[str, dict[str, Any]] = {}
    kinds: set[str] = set()
    covered: set[str] = set()
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            fail(f"request.validation.required_checks[{index}]: expected mapping")
        check_id = nonempty_string(check.get("id"), f"request.validation.required_checks[{index}].id")
        if check_id in by_id:
            fail(f"request.validation.required_checks: duplicate id {check_id}")
        kind = check.get("kind")
        if kind not in CHECK_KINDS:
            fail(f"request.validation.required_checks[{index}].kind: unsupported kind")
        kinds.add(kind)
        linked = set(
            string_list(
                check.get("acceptance_ids"),
                f"request.validation.required_checks[{index}].acceptance_ids",
                allow_empty=False,
            )
        )
        unknown = linked - acceptance_ids
        if unknown:
            fail(f"request.validation.required_checks[{index}]: unknown acceptance ids {sorted(unknown)}")
        covered.update(linked)
        if kind == "command":
            nonempty_string(check.get("command"), f"request.validation.required_checks[{index}].command")
        else:
            nonempty_string(check.get("criterion"), f"request.validation.required_checks[{index}].criterion")
        by_id[check_id] = check

    missing = acceptance_ids - covered
    if missing:
        fail(f"request.validation: acceptance ids without required verification {sorted(missing)}")
    if mode == "commands" and kinds != {"command"}:
        fail("request.validation.mode commands requires only command checks")
    if mode == "semantic" and kinds != {"semantic"}:
        fail("request.validation.mode semantic requires only semantic checks")
    if mode == "mixed" and kinds != {"command", "semantic"}:
        fail("request.validation.mode mixed requires command and semantic checks")
    return by_id


def validate_invocation(value: Any, label: str, *, required: bool) -> None:
    if value is None and not required:
        return
    if not isinstance(value, dict):
        fail(f"{label}: expected mapping")
    nonempty_string(value.get("command"), f"{label}.command")
    exit_code = value.get("exit_code")
    if isinstance(exit_code, bool) or not isinstance(exit_code, int):
        fail(f"{label}.exit_code: expected integer")
    nonempty_string(value.get("evidence"), f"{label}.evidence")


def routing_runtime_fallback(
    routing: dict[str, Any],
    list_key: str,
    reason_key: str,
) -> tuple[list[str], str | None]:
    value = routing.get(list_key)
    if value is None:
        value = []
    excluded = string_list(value, f"request.routing.{list_key}")
    reason = routing.get(reason_key)
    if not excluded:
        return [], None
    nonempty_string(reason, f"request.routing.{reason_key}")
    return excluded, reason


def validate_resolved_route(
    value: Any,
    label: str,
    *,
    expected: dict[str, Any],
    template_mode: bool,
) -> None:
    if not isinstance(value, dict):
        fail(f"{label}: expected mapping")
    for key in ("profile", "backend", "model", "effort"):
        actual = nonempty_string(value.get(key), f"{label}.{key}")
        if not template_mode and actual != expected[key]:
            fail(
                f"{label}.{key}: route mismatch, expected {expected[key]!r}, got {actual!r}"
            )
    preflight = value.get("preflight")
    if not isinstance(preflight, dict):
        fail(f"{label}.preflight: expected mapping")
    status = nonempty_string(preflight.get("status"), f"{label}.preflight.status").lower()
    if status != "pass":
        fail(f"{label}.preflight.status: expected pass")
    command = nonempty_string(preflight.get("command"), f"{label}.preflight.command")
    exit_code = preflight.get("exit_code")
    if isinstance(exit_code, bool) or not isinstance(exit_code, int):
        fail(f"{label}.preflight.exit_code: expected integer")
    if exit_code != 0:
        fail(f"{label}.preflight.exit_code: expected 0")
    nonempty_string(preflight.get("evidence"), f"{label}.preflight.evidence")
    if not template_mode and "route_preflight.py" not in command:
        fail(f"{label}.preflight.command must invoke route_preflight.py")


def validate_governance(doc: dict[str, Any], *, template_mode: bool) -> None:
    governance = doc.get("governance")
    if not isinstance(governance, dict):
        fail("request.governance: expected mapping")
    start_gate = governance.get("project_start_gate")
    if not isinstance(start_gate, dict):
        fail("request.governance.project_start_gate: expected mapping")
    status = start_gate.get("status")
    if status not in {"APPROVED", "NOT_REQUIRED"}:
        fail("request.governance.project_start_gate.status must be APPROVED or NOT_REQUIRED")
    nonempty_string(start_gate.get("ref"), "request.governance.project_start_gate.ref")

    controller = governance.get("controller")
    if not isinstance(controller, dict):
        fail("request.governance.controller: expected mapping")
    nonempty_string(controller.get("id"), "request.governance.controller.id")
    session = controller.get("session")
    if session is not None:
        nonempty_string(session, "request.governance.controller.session")

    override = governance.get("controller_worker_override")
    if not isinstance(override, dict):
        fail("request.governance.controller_worker_override: expected mapping")
    if not isinstance(override.get("allowed"), bool):
        fail("request.governance.controller_worker_override.allowed must be boolean")
    reason = override.get("reason")
    if override["allowed"]:
        nonempty_string(reason, "request.governance.controller_worker_override.reason")
    elif reason not in (None, "") and not template_mode:
        fail("request.governance.controller_worker_override.reason must be empty when not allowed")


def validate_request(doc: dict[str, Any], *, template_mode: bool = False) -> None:
    if not template_mode:
        reject_placeholders(doc, "request")
    validate_identity(doc, "request")
    validate_workspace(doc, "request")
    validate_governance(doc, template_mode=template_mode)
    if doc.get("purpose") not in REQUEST_PURPOSES:
        fail("request.purpose: expected execute")
    for key in ("objective", "complexity", "risk", "task_kind"):
        nonempty_string(doc.get(key), f"request.{key}")

    scope = doc.get("scope")
    if not isinstance(scope, dict):
        fail("request.scope: expected mapping")
    validate_repo_relative_paths(scope.get("allowed_paths"), "request.scope.allowed_paths")
    validate_repo_relative_paths(scope.get("forbidden_paths"), "request.scope.forbidden_paths")

    string_list(doc.get("inputs"), "request.inputs")
    string_list(doc.get("dependencies"), "request.dependencies")
    acceptance_ids = validate_acceptance(doc)
    validate_required_checks(doc, acceptance_ids)
    string_list(doc.get("stop_conditions"), "request.stop_conditions", allow_empty=False)

    routing = doc.get("routing")
    if not isinstance(routing, dict):
        fail("request.routing: expected mapping")
    for profile_key, reason_key in (
        ("execution_profile", "execution_profile_override_reason"),
        ("review_profile", "review_profile_override_reason"),
    ):
        profile = nonempty_string(routing.get(profile_key), f"request.routing.{profile_key}")
        reason = routing.get(reason_key)
        if profile != "auto":
            nonempty_string(reason, f"request.routing.{reason_key}")

    retry = doc.get("retry")
    if not isinstance(retry, dict):
        fail("request.retry: expected mapping")
    attempt_number = positive_integer(retry.get("attempt_number"), "request.retry.attempt_number")
    max_retries = nonnegative_integer(retry.get("max_retries"), "request.retry.max_retries")
    failures = nonnegative_integer(
        retry.get("same_fingerprint_failures"),
        "request.retry.same_fingerprint_failures",
    )
    if attempt_number > max_retries + 1:
        fail("request.retry.attempt_number exceeds initial attempt + max_retries")
    if failures > max_retries:
        fail("request.retry.same_fingerprint_failures exceeds max_retries")
    fingerprint = retry.get("fingerprint")
    if failures:
        nonempty_string(fingerprint, "request.retry.fingerprint")

    execution_override = (
        None if routing["execution_profile"] == "auto" else routing["execution_profile"]
    )
    review_override = None if routing["review_profile"] == "auto" else routing["review_profile"]
    execution_excluded, execution_reason = routing_runtime_fallback(
        routing,
        "execution_excluded_backends",
        "execution_fallback_reason",
    )
    review_excluded, review_reason = routing_runtime_fallback(
        routing,
        "review_excluded_backends",
        "review_fallback_reason",
    )
    expected_execution = resolve_route(
        purpose="execute",
        complexity=doc["complexity"],
        risk=doc["risk"],
        task_kind=doc["task_kind"],
        failure_count=failures,
        override=execution_override,
        override_reason=routing.get("execution_profile_override_reason"),
        excluded_backends=execution_excluded,
        fallback_reason=execution_reason,
    )
    validate_resolved_route(
        routing.get("resolved_execution"),
        "request.routing.resolved_execution",
        expected=expected_execution,
        template_mode=template_mode,
    )
    expected_review = resolve_route(
        purpose="review",
        complexity=doc["complexity"],
        risk=doc["risk"],
        task_kind=doc["task_kind"],
        failure_count=failures,
        override=review_override,
        override_reason=routing.get("review_profile_override_reason"),
        worker_backend=expected_execution["backend"],
        excluded_backends=review_excluded,
        fallback_reason=review_reason,
    )
    validate_resolved_route(
        routing.get("resolved_review"),
        "request.routing.resolved_review",
        expected=expected_review,
        template_mode=template_mode,
    )


def validate_result_check(check: Any, index: int) -> tuple[str, str]:
    if not isinstance(check, dict):
        fail(f"result.verification.checks[{index}]: expected mapping")
    check_id = nonempty_string(check.get("id"), f"result.verification.checks[{index}].id")
    kind = check.get("kind")
    if kind not in CHECK_KINDS:
        fail(f"result.verification.checks[{index}].kind: unsupported kind")
    nonempty_string(check.get("evidence"), f"result.verification.checks[{index}].evidence")
    if kind == "command":
        nonempty_string(check.get("command"), f"result.verification.checks[{index}].command")
        exit_code = check.get("exit_code")
        if isinstance(exit_code, bool) or not isinstance(exit_code, int):
            fail(f"result.verification.checks[{index}].exit_code: expected integer")
    else:
        nonempty_string(check.get("conclusion"), f"result.verification.checks[{index}].conclusion")
    return check_id, kind


def validate_review_independence(review: dict[str, Any], worker: dict[str, Any]) -> None:
    reviewer_type = review.get("reviewer_type")
    if reviewer_type not in REVIEWER_TYPES:
        fail("result.review.reviewer_type: expected model or human")
    nonempty_string(review.get("independence_evidence"), "result.review.independence_evidence")
    positive_integer(review.get("review_revision"), "result.review.review_revision")

    if reviewer_type == "model":
        nonempty_string(review.get("backend"), "result.review.backend")
        nonempty_string(review.get("model"), "result.review.model")
        nonempty_string(review.get("effort"), "result.review.effort")
        review_session = nonempty_string(review.get("session"), "result.review.session")
        worker_session = nonempty_string(worker.get("session"), "result.worker.session")
        if review_session == worker_session:
            fail("result.review.session must differ from result.worker.session")
        validate_invocation(review.get("invocation"), "result.review.invocation", required=True)
    else:
        nonempty_string(review.get("reviewer_id"), "result.review.reviewer_id")


def validate_result(doc: dict[str, Any], *, template_mode: bool = False) -> None:
    if not template_mode:
        reject_placeholders(doc, "result")
    validate_identity(doc, "result")
    validate_workspace(doc, "result")
    status = doc.get("status")
    if status not in RESULT_STATUSES:
        fail(f"result.status: unsupported status {status!r}")

    delivery = doc.get("delivery")
    if not isinstance(delivery, dict):
        fail("result.delivery: expected mapping")

    worker = doc.get("worker")
    if not isinstance(worker, dict):
        fail("result.worker: expected mapping")
    worker_status = worker.get("status")
    if worker_status not in WORKER_STATUSES:
        fail("result.worker.status: unsupported status")
    for key in ("role", "profile", "backend", "model", "effort"):
        nonempty_string(worker.get(key), f"result.worker.{key}")
    execution_mode = worker.get("execution_mode")
    if execution_mode not in WORKER_EXECUTION_MODES:
        fail("result.worker.execution_mode must be delegated or controller_override")
    if execution_mode == "controller_override":
        nonempty_string(worker.get("override_reason"), "result.worker.override_reason")
    if worker_status == "COMPLETED":
        nonempty_string(worker.get("session"), "result.worker.session")
        validate_invocation(worker.get("invocation"), "result.worker.invocation", required=True)

    validate_repo_relative_paths(doc.get("changed_paths"), "result.changed_paths")

    verification = doc.get("verification")
    if not isinstance(verification, dict):
        fail("result.verification: expected mapping")
    mode = verification.get("mode")
    if mode not in VERIFICATION_MODES:
        fail("result.verification.mode: unsupported mode")
    verification_result = verification.get("result")
    if verification_result not in VERIFICATION_RESULTS:
        fail("result.verification.result: unsupported result")
    checks = verification.get("checks")
    if not isinstance(checks, list):
        fail("result.verification.checks: expected list")
    seen_checks: set[str] = set()
    check_kinds: set[str] = set()
    for index, check in enumerate(checks):
        check_id, kind = validate_result_check(check, index)
        if check_id in seen_checks:
            fail(f"result.verification.checks: duplicate id {check_id}")
        seen_checks.add(check_id)
        check_kinds.add(kind)
        if verification_result == "PASS" and kind == "command" and check.get("exit_code") != 0:
            fail("result.verification: PASS cannot include a non-zero command exit code")
    if verification_result == "PASS" and not checks:
        fail("result.verification.checks: PASS requires evidence")
    if mode == "commands" and check_kinds and check_kinds != {"command"}:
        fail("result.verification.mode commands requires only command checks")
    if mode == "semantic" and check_kinds and check_kinds != {"semantic"}:
        fail("result.verification.mode semantic requires only semantic checks")
    if mode == "mixed" and verification_result == "PASS" and check_kinds != {"command", "semantic"}:
        fail("result.verification.mode mixed PASS requires command and semantic checks")

    failure = doc.get("failure")
    if not isinstance(failure, dict):
        fail("result.failure: expected mapping")
    failure_count = nonnegative_integer(
        failure.get("same_fingerprint_failures"),
        "result.failure.same_fingerprint_failures",
    )
    failure_signal = (
        status in {"FAILED", "NEEDS_HUMAN"}
        or worker_status in {"FAILED", "NEEDS_HUMAN"}
        or verification_result == "FAIL"
    )

    review = doc.get("review")
    if not isinstance(review, dict):
        fail("result.review: expected mapping")
    review_status = review.get("status")
    if review_status not in REVIEW_STATUSES:
        fail("result.review.status: unsupported status")
    nonempty_string(review.get("role"), "result.review.role")
    if review_status == "PENDING":
        nonempty_string(review.get("profile"), "result.review.profile")
        string_list(review.get("evidence"), "result.review.evidence")
    else:
        evidence = string_list(review.get("evidence"), "result.review.evidence", allow_empty=False)
        if not evidence:
            fail("result.review.evidence: completed review requires evidence")
        validate_review_independence(review, worker)
        if review_status in {"FAIL", "NEEDS_HUMAN"}:
            failure_signal = True

    if failure_signal or failure_count:
        nonempty_string(failure.get("fingerprint"), "result.failure.fingerprint")
        nonempty_string(failure.get("category"), "result.failure.category")
        nonempty_string(failure.get("error_code"), "result.failure.error_code")

    integration = doc.get("project_integration")
    if not isinstance(integration, dict):
        fail("result.project_integration: expected mapping")
    if integration.get("status") != "NOT_EVALUATED":
        fail("result.project_integration.status must remain NOT_EVALUATED in execution-layer output")

    baseline_kind = doc["workspace"]["baseline"]["kind"]
    if status in {"READY_FOR_REVIEW", "REVIEW_PASSED"}:
        if worker_status != "COMPLETED":
            fail(f"result.status {status} requires worker COMPLETED")
        if verification_result != "PASS":
            fail(f"result.status {status} requires verification PASS")
        if baseline_kind == "git":
            nonempty_string(delivery.get("branch"), "result.delivery.branch")
            nonempty_string(delivery.get("commit"), "result.delivery.commit")

    if status == "READY_FOR_REVIEW" and review_status != "PENDING":
        fail("READY_FOR_REVIEW requires review PENDING")
    if status == "REVIEW_PASSED" and review_status != "PASS":
        fail("REVIEW_PASSED requires review PASS")
    if status == "FAILED" and not failure_signal:
        fail("FAILED requires worker, verification, or review failure evidence")
    if status == "NEEDS_HUMAN" and not (
        worker_status == "NEEDS_HUMAN"
        or review_status == "NEEDS_HUMAN"
        or failure.get("category") in {"requirement/input ambiguity", "permission/external system"}
    ):
        fail("NEEDS_HUMAN requires an explicit blocking signal")


def validate_pair(request: dict[str, Any], result: dict[str, Any]) -> None:
    for key in ("task_id", "task_revision", "attempt_id"):
        if request.get(key) != result.get(key):
            fail(f"request/result identity mismatch: {key}")
    if request["workspace"]["project_root"] != result["workspace"]["project_root"]:
        fail("request/result identity mismatch: workspace.project_root")
    if request["workspace"]["baseline"] != result["workspace"]["baseline"]:
        fail("request/result identity mismatch: workspace.baseline")

    governance = request["governance"]
    worker = result["worker"]
    execution_mode = worker["execution_mode"]
    if execution_mode == "controller_override":
        override = governance["controller_worker_override"]
        if not override["allowed"]:
            fail("controller_override is not authorized by request governance")
        if worker.get("override_reason") != override.get("reason"):
            fail("result.worker.override_reason must match authorized controller override reason")
    else:
        controller_session = governance["controller"].get("session")
        if controller_session and worker.get("session") == controller_session:
            fail("delegated worker session must differ from controller session")
        expected_worker = request["routing"]["resolved_execution"]
        for key in ("profile", "backend", "model", "effort"):
            if worker.get(key) != expected_worker.get(key):
                fail(f"result.worker.{key} does not match resolved execution route")

    review = result["review"]
    expected_review = request["routing"]["resolved_review"]
    if review.get("profile") != expected_review.get("profile"):
        fail("result.review.profile does not match resolved review route")
    if review.get("status") != "PENDING" and review.get("reviewer_type") == "model":
        for key in ("backend", "model", "effort"):
            if review.get(key) != expected_review.get(key):
                fail(f"result.review.{key} does not match resolved review route")

    allowed = validate_repo_relative_paths(
        request["scope"]["allowed_paths"],
        "request.scope.allowed_paths",
    )
    forbidden = validate_repo_relative_paths(
        request["scope"]["forbidden_paths"],
        "request.scope.forbidden_paths",
    )
    changed = validate_repo_relative_paths(result["changed_paths"], "result.changed_paths")
    for path in changed:
        if forbidden and any(path_matches(path, pattern) for pattern in forbidden):
            fail(f"result.changed_paths: forbidden path changed: {path}")
        if not any(path_matches(path, pattern) for pattern in allowed):
            fail(f"result.changed_paths: path outside allowed scope: {path}")

    acceptance_ids = validate_acceptance(request)
    required = validate_required_checks(request, acceptance_ids)
    result_checks = result["verification"]["checks"]
    actual: dict[str, dict[str, Any]] = {}
    for index, check in enumerate(result_checks):
        check_id = nonempty_string(check.get("id"), f"result.verification.checks[{index}].id")
        if check_id in actual:
            fail(f"result.verification.checks: duplicate id {check_id}")
        actual[check_id] = check

    required_ids = set(required)
    actual_ids = set(actual)
    missing = required_ids - actual_ids
    unexpected = actual_ids - required_ids
    if missing and result.get("status") in {"READY_FOR_REVIEW", "REVIEW_PASSED"}:
        fail(f"result.verification: missing required checks {sorted(missing)}")
    if unexpected:
        fail(f"result.verification: unauthorized checks {sorted(unexpected)}")
    if result["verification"]["mode"] != request["validation"]["mode"]:
        fail("request/result verification mode mismatch")

    for check_id, observed in actual.items():
        expected = required[check_id]
        if observed.get("kind") != expected.get("kind"):
            fail(f"result.verification.check {check_id}: kind mismatch")
        if expected["kind"] == "command" and observed.get("command") != expected.get("command"):
            fail(f"result.verification.check {check_id}: command mismatch")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--result", type=Path)
    parser.add_argument(
        "--mode",
        choices=["actual", "template"],
        default="actual",
        help="template validates reusable placeholders; actual rejects them",
    )
    args = parser.parse_args()
    if not args.request and not args.result:
        parser.error("provide --request, --result, or both")

    template_mode = args.mode == "template"
    try:
        request = load_yaml(args.request) if args.request else None
        result = load_yaml(args.result) if args.result else None
        if request is not None:
            validate_request(request, template_mode=template_mode)
        if result is not None:
            validate_result(result, template_mode=template_mode)
        if request is not None and result is not None:
            validate_pair(request, result)
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"execution contract validation failed: {error}", file=sys.stderr)
        return 1

    print(f"execution contract validation passed ({args.mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
