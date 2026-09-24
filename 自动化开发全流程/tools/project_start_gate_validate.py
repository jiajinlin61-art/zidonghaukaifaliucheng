"""Validate the project start / development-plan approval gate.

Schema 1.1 adds the FULL-mode design-baseline gate: FULL projects need the plan
approval plus a second approval of the design artifacts (technical selection,
PRD, prototype, architecture, API contract, implementation plan) before
implementation. FAST/STANDARD keep the single scaled plan approval; schema 1.0
stays valid for them, while legacy 1.0 FULL gate files fail closed until they
are migrated to 1.1.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

import yaml

MODES = {"FAST", "STANDARD", "FULL"}
COMPLEXITIES = {"TRIVIAL", "SIMPLE", "STANDARD", "COMPLEX", "CRITICAL"}
RISKS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
GATE_SCHEMA_VERSIONS = {"1.0", "1.1"}
DESIGN_ARTIFACTS = (
    "technical_selection",
    "prd",
    "prototype",
    "architecture",
    "api_contract",
    "implementation_plan",
)
ARTIFACT_STATUSES = {"ready", "not_applicable"}


def fail(message: str) -> None:
    raise ValueError(message)


def load_gate(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail("project start gate must be a mapping")
    return value


def required_by_policy(doc: dict[str, Any]) -> bool:
    mode = doc.get("mode")
    complexity = doc.get("complexity")
    risk = doc.get("risk")
    if mode not in MODES:
        fail("mode must be FAST, STANDARD, or FULL")
    if complexity not in COMPLEXITIES:
        fail("complexity must be TRIVIAL, SIMPLE, STANDARD, COMPLEX, or CRITICAL")
    if risk not in RISKS:
        fail("risk must be LOW, MEDIUM, HIGH, or CRITICAL")
    return (
        mode == "FULL"
        or complexity in {"COMPLEX", "CRITICAL"}
        or risk in {"HIGH", "CRITICAL"}
        or bool(doc.get("cross_system"))
        or bool(doc.get("architecture_change"))
        or bool(doc.get("explicit_plan_approval_required"))
    )


def validate_design_gate(doc: dict[str, Any]) -> bool:
    """Validate the FULL-mode design-baseline gate; return its approval state."""
    design = doc.get("design_gate")
    if doc.get("mode") != "FULL":
        if design is not None and (not isinstance(design, dict) or design.get("required", False)):
            fail("design_gate is only used by FULL mode; FAST/STANDARD use one scaled plan approval")
        if "has_ui" in doc and not isinstance(doc["has_ui"], bool):
            fail("has_ui must be boolean")
        return True

    has_ui = doc.get("has_ui")
    has_backend = doc.get("has_backend")
    major_technical_change = doc.get("major_technical_change")
    if not isinstance(has_ui, bool):
        fail("has_ui must be boolean for schema 1.1 FULL gates")
    if not isinstance(has_backend, bool):
        fail("has_backend must be boolean for schema 1.1 FULL gates")
    if not isinstance(major_technical_change, bool):
        fail("major_technical_change must be boolean for schema 1.1 FULL gates")
    if not isinstance(design, dict):
        fail("design_gate must be a mapping for FULL mode")
    if design.get("required") is not True:
        fail("design_gate.required must be true for FULL mode")

    artifacts = design.get("artifacts")
    if not isinstance(artifacts, dict):
        fail("design_gate.artifacts must be a mapping")
    for name in DESIGN_ARTIFACTS:
        entry = artifacts.get(name)
        if not isinstance(entry, dict):
            fail(f"design_gate.artifacts.{name} must be a mapping")
        status = entry.get("status")
        if status not in ARTIFACT_STATUSES:
            fail(f"design_gate.artifacts.{name}.status must be ready or not_applicable")
        if status == "not_applicable":
            reason = entry.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                fail(f"design_gate.artifacts.{name}.reason is required when status is not_applicable")

    must_be_ready = ["prd", "architecture", "implementation_plan"]
    if doc.get("project_kind") == "new" or major_technical_change:
        must_be_ready.append("technical_selection")
    if has_ui:
        must_be_ready.append("prototype")
    if has_ui and has_backend:
        must_be_ready.append("api_contract")
    for name in must_be_ready:
        if artifacts[name]["status"] != "ready":
            fail(f"design_gate.artifacts.{name}.status must be ready for this FULL gate")
    if not has_ui and artifacts["prototype"]["status"] != "not_applicable":
        fail("design_gate.artifacts.prototype.status must be not_applicable with a reason when has_ui is false")
    if not has_backend and artifacts["api_contract"]["status"] != "not_applicable":
        fail("design_gate.artifacts.api_contract.status must be not_applicable with a reason when has_backend is false")

    user_approved = design.get("user_approved")
    if not isinstance(user_approved, bool):
        fail("design_gate.user_approved must be boolean")
    approval_ref = design.get("approval_ref")
    if user_approved and (not isinstance(approval_ref, str) or not approval_ref.strip()):
        fail("design_gate.approval_ref is required when the design gate is approved")
    return user_approved


def validate_gate(doc: dict[str, Any], *, require_implementation: bool = False) -> None:
    version = doc.get("schema_version")
    if version not in GATE_SCHEMA_VERSIONS:
        fail("unsupported schema_version")
    if version == "1.0" and doc.get("mode") == "FULL":
        fail("legacy schema 1.0 FULL gate must migrate to schema 1.1 with a design_gate before implementation")
    if doc.get("project_kind") not in {"new", "existing"}:
        fail("project_kind must be new or existing")

    required = required_by_policy(doc)
    gate = doc.get("plan_gate")
    if not isinstance(gate, dict):
        fail("plan_gate must be a mapping")
    if not isinstance(gate.get("required"), bool):
        fail("plan_gate.required must be boolean")
    if gate["required"] != required:
        fail(
            f"plan_gate.required is inconsistent with policy: expected {str(required).lower()}"
        )

    for key in ("requirements_read", "architecture_ready", "development_plan_ready", "user_approved"):
        if not isinstance(gate.get(key), bool):
            fail(f"plan_gate.{key} must be boolean")

    approval_ref = gate.get("approval_ref")
    if required and gate["user_approved"]:
        if not isinstance(approval_ref, str) or not approval_ref.strip():
            fail("plan_gate.approval_ref is required when a required gate is approved")

    design_approved = True
    if version == "1.1":
        design_approved = validate_design_gate(doc)

    implementation = doc.get("implementation")
    if not isinstance(implementation, dict):
        fail("implementation must be a mapping")
    if not isinstance(implementation.get("allowed"), bool):
        fail("implementation.allowed must be boolean")

    prerequisites_ready = (
        gate["requirements_read"]
        and gate["architecture_ready"]
        and gate["development_plan_ready"]
    )
    expected_allowed = (
        prerequisites_ready
        and (not required or gate["user_approved"])
        and design_approved
    )
    if implementation["allowed"] != expected_allowed:
        fail(
            "implementation.allowed is inconsistent with plan-gate/design-gate prerequisites/approval"
        )

    if not implementation["allowed"]:
        reason = implementation.get("blocked_reason")
        if not isinstance(reason, str) or not reason.strip():
            fail("implementation.blocked_reason is required while implementation is blocked")

    if require_implementation and not implementation["allowed"]:
        fail("implementation is BLOCKED by Project Start / Plan Approval / Design Baseline Gate")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--require-implementation", action="store_true")
    args = parser.parse_args()
    try:
        validate_gate(load_gate(args.gate), require_implementation=args.require_implementation)
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"project start gate validation failed: {error}", file=sys.stderr)
        return 1
    print("project start gate validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
