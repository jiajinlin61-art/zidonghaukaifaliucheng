import copy
import unittest

from tools.project_start_gate_validate import validate_gate


def valid_required_gate():
    return {
        "schema_version": "1.1",
        "project_kind": "new",
        "mode": "FULL",
        "complexity": "COMPLEX",
        "risk": "HIGH",
        "cross_system": True,
        "architecture_change": True,
        "has_ui": True,
        "has_backend": True,
        "major_technical_change": False,
        "explicit_plan_approval_required": False,
        "plan_gate": {
            "required": True,
            "requirements_read": True,
            "architecture_ready": True,
            "development_plan_ready": True,
            "user_approved": True,
            "approval_ref": "chat-approval-2026-09-21",
        },
        "design_gate": {
            "required": True,
            "artifacts": {
                "technical_selection": {"status": "ready", "reason": ""},
                "prd": {"status": "ready", "reason": ""},
                "prototype": {"status": "ready", "reason": ""},
                "architecture": {"status": "ready", "reason": ""},
                "api_contract": {"status": "ready", "reason": ""},
                "implementation_plan": {"status": "ready", "reason": ""},
            },
            "user_approved": True,
            "approval_ref": "chat-approval-2026-09-22",
        },
        "implementation": {
            "allowed": True,
            "blocked_reason": "",
        },
    }


def legacy_full_gate():
    doc = valid_required_gate()
    doc["schema_version"] = "1.0"
    doc.pop("has_ui")
    doc.pop("design_gate")
    return doc


def valid_standard_gate_v1_1():
    return {
        "schema_version": "1.1",
        "project_kind": "existing",
        "mode": "STANDARD",
        "complexity": "STANDARD",
        "risk": "MEDIUM",
        "cross_system": False,
        "architecture_change": False,
        "explicit_plan_approval_required": True,
        "plan_gate": {
            "required": True,
            "requirements_read": True,
            "architecture_ready": True,
            "development_plan_ready": True,
            "user_approved": True,
            "approval_ref": "chat-approval-2026-09-23",
        },
        "implementation": {
            "allowed": True,
            "blocked_reason": "",
        },
    }


class ProjectStartGateValidationTest(unittest.TestCase):
    def test_required_gate_allows_implementation_after_approval(self):
        validate_gate(valid_required_gate(), require_implementation=True)

    def test_complex_project_requires_gate(self):
        doc = valid_required_gate()
        doc["plan_gate"]["required"] = False
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            validate_gate(doc)

    def test_required_gate_blocks_without_user_approval(self):
        doc = valid_required_gate()
        doc["plan_gate"]["user_approved"] = False
        doc["plan_gate"]["approval_ref"] = None
        doc["implementation"]["allowed"] = False
        doc["implementation"]["blocked_reason"] = "Awaiting plan approval"
        validate_gate(doc)
        with self.assertRaisesRegex(ValueError, "BLOCKED"):
            validate_gate(doc, require_implementation=True)

    def test_approval_requires_reference(self):
        doc = valid_required_gate()
        doc["plan_gate"]["approval_ref"] = ""
        with self.assertRaisesRegex(ValueError, "approval_ref"):
            validate_gate(doc)

    def test_fast_low_risk_project_can_skip_plan_approval(self):
        doc = valid_required_gate()
        doc.update(
            {
                "mode": "FAST",
                "complexity": "SIMPLE",
                "risk": "LOW",
                "cross_system": False,
                "architecture_change": False,
            }
        )
        doc.pop("has_ui")
        doc.pop("has_backend")
        doc.pop("major_technical_change")
        doc.pop("design_gate")
        doc["plan_gate"]["required"] = False
        doc["plan_gate"]["user_approved"] = False
        doc["plan_gate"]["approval_ref"] = None
        validate_gate(doc, require_implementation=True)

    def test_missing_prerequisite_blocks_even_when_approved(self):
        doc = valid_required_gate()
        doc["plan_gate"]["development_plan_ready"] = False
        doc["implementation"]["allowed"] = False
        doc["implementation"]["blocked_reason"] = "Plan not ready"
        validate_gate(doc)
        with self.assertRaisesRegex(ValueError, "BLOCKED"):
            validate_gate(doc, require_implementation=True)

    def test_legacy_full_schema_1_0_fails_closed_until_migrated(self):
        with self.assertRaisesRegex(ValueError, "migrate"):
            validate_gate(legacy_full_gate())

    def test_legacy_fast_schema_1_0_behavior_is_preserved(self):
        doc = legacy_full_gate()
        doc.update(
            {
                "mode": "FAST",
                "complexity": "SIMPLE",
                "risk": "LOW",
                "cross_system": False,
                "architecture_change": False,
            }
        )
        doc["plan_gate"]["required"] = False
        doc["plan_gate"]["user_approved"] = False
        doc["plan_gate"]["approval_ref"] = None
        validate_gate(doc, require_implementation=True)

    def test_full_design_gate_missing_fails(self):
        doc = valid_required_gate()
        doc.pop("design_gate")
        with self.assertRaisesRegex(ValueError, "design_gate"):
            validate_gate(doc)

    def test_full_design_gate_must_be_required(self):
        doc = valid_required_gate()
        doc["design_gate"]["required"] = False
        with self.assertRaisesRegex(ValueError, "design_gate.required"):
            validate_gate(doc)

    def test_full_design_gate_blocks_implementation_without_approval(self):
        doc = valid_required_gate()
        doc["design_gate"]["user_approved"] = False
        doc["design_gate"]["approval_ref"] = None
        doc["implementation"]["allowed"] = False
        doc["implementation"]["blocked_reason"] = "Awaiting design-baseline approval"
        validate_gate(doc)
        with self.assertRaisesRegex(ValueError, "BLOCKED"):
            validate_gate(doc, require_implementation=True)

    def test_full_missing_design_artifact_fails(self):
        doc = valid_required_gate()
        doc["design_gate"]["artifacts"].pop("prd")
        with self.assertRaisesRegex(ValueError, "prd"):
            validate_gate(doc)

    def test_artifact_not_applicable_requires_reason(self):
        doc = valid_required_gate()
        doc["has_ui"] = False
        doc["design_gate"]["artifacts"]["prototype"] = {"status": "not_applicable", "reason": ""}
        with self.assertRaisesRegex(ValueError, "reason"):
            validate_gate(doc)

    def test_full_no_ui_project_requires_prototype_not_applicable(self):
        doc = valid_required_gate()
        doc["has_ui"] = False
        with self.assertRaisesRegex(ValueError, "prototype"):
            validate_gate(doc)

    def test_full_no_ui_project_with_reasoned_na_prototype_passes(self):
        doc = valid_required_gate()
        doc["has_ui"] = False
        doc["design_gate"]["artifacts"]["prototype"] = {
            "status": "not_applicable",
            "reason": "No UI; batch CLI tool",
        }
        validate_gate(doc, require_implementation=True)

    def test_full_ui_project_requires_prototype_and_api_contract(self):
        doc = valid_required_gate()
        doc["design_gate"]["artifacts"]["prototype"] = {
            "status": "not_applicable",
            "reason": "Screens already fixed",
        }
        with self.assertRaisesRegex(ValueError, "prototype"):
            validate_gate(doc)
        doc = valid_required_gate()
        doc["design_gate"]["artifacts"]["api_contract"] = {
            "status": "not_applicable",
            "reason": "Static pages only",
        }
        with self.assertRaisesRegex(ValueError, "api_contract"):
            validate_gate(doc)

    def test_full_existing_project_may_reuse_stack_with_reason(self):
        doc = valid_required_gate()
        doc["project_kind"] = "existing"
        doc["design_gate"]["artifacts"]["technical_selection"] = {
            "status": "not_applicable",
            "reason": "Existing project reuses its current stack",
        }
        validate_gate(doc, require_implementation=True)

    def test_full_new_project_requires_technical_selection(self):
        doc = valid_required_gate()
        doc["design_gate"]["artifacts"]["technical_selection"] = {
            "status": "not_applicable",
            "reason": "Stack chosen earlier",
        }
        with self.assertRaisesRegex(ValueError, "technical_selection"):
            validate_gate(doc)

    def test_existing_project_with_major_technical_change_requires_selection(self):
        doc = valid_required_gate()
        doc["project_kind"] = "existing"
        doc["major_technical_change"] = True
        doc["design_gate"]["artifacts"]["technical_selection"] = {
            "status": "not_applicable",
            "reason": "Existing project",
        }
        with self.assertRaisesRegex(ValueError, "technical_selection"):
            validate_gate(doc)

    def test_ui_without_backend_does_not_require_api_contract(self):
        doc = valid_required_gate()
        doc["has_backend"] = False
        doc["design_gate"]["artifacts"]["api_contract"] = {
            "status": "not_applicable",
            "reason": "Static UI with no server code",
        }
        validate_gate(doc, require_implementation=True)

    def test_backend_without_ui_does_not_require_prototype(self):
        doc = valid_required_gate()
        doc["has_ui"] = False
        doc["design_gate"]["artifacts"]["prototype"] = {
            "status": "not_applicable",
            "reason": "Backend-only service",
        }
        validate_gate(doc, require_implementation=True)

    def test_full_core_design_artifacts_cannot_be_not_applicable(self):
        doc = valid_required_gate()
        doc["design_gate"]["artifacts"]["architecture"] = {
            "status": "not_applicable",
            "reason": "Simple project",
        }
        with self.assertRaisesRegex(ValueError, "architecture"):
            validate_gate(doc)

    def test_design_approval_requires_reference(self):
        doc = valid_required_gate()
        doc["design_gate"]["approval_ref"] = ""
        with self.assertRaisesRegex(ValueError, "approval_ref"):
            validate_gate(doc)

    def test_full_schema_1_1_requires_has_ui(self):
        doc = valid_required_gate()
        doc.pop("has_ui")
        with self.assertRaisesRegex(ValueError, "has_ui"):
            validate_gate(doc)

    def test_standard_schema_1_1_without_design_gate_validates(self):
        validate_gate(valid_standard_gate_v1_1(), require_implementation=True)

    def test_standard_schema_1_1_rejects_design_gate(self):
        doc = valid_standard_gate_v1_1()
        doc["design_gate"] = copy.deepcopy(valid_required_gate()["design_gate"])
        with self.assertRaisesRegex(ValueError, "design_gate"):
            validate_gate(doc)


if __name__ == "__main__":
    unittest.main()
