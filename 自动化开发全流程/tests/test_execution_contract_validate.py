import unittest
from pathlib import Path

import yaml

from tools.execution_contract_validate import (
    validate_pair,
    validate_request,
    validate_result,
)


def valid_request():
    return {
        "schema_version": "1.4",
        "task_id": "P1-T01",
        "task_revision": 1,
        "attempt_id": "P1-T01-r1-a1",
        "objective": "Implement example feature",
        "purpose": "execute",
        "complexity": "STANDARD",
        "risk": "MEDIUM",
        "task_kind": "general",
        "workspace": {
            "project_root": r"E:\temp\example",
            "baseline": {"kind": "git", "ref": "abc123"},
        },
        "governance": {
            "project_start_gate": {
                "status": "APPROVED",
                "ref": "project-start-gate-1",
            },
            "controller": {
                "id": "gpt-taskboard",
                "session": "controller-session-1",
            },
            "controller_worker_override": {
                "allowed": False,
                "reason": None,
            },
        },
        "scope": {
            "allowed_paths": ["src/example/**", "tests/example/**"],
            "forbidden_paths": ["src/example/secrets/**"],
        },
        "inputs": [],
        "dependencies": [],
        "acceptance": [
            {"id": "A1", "criterion": "Feature behavior works"},
            {"id": "A2", "criterion": "Regression test passes"},
        ],
        "validation": {
            "mode": "mixed",
            "required_checks": [
                {
                    "id": "V1",
                    "kind": "command",
                    "acceptance_ids": ["A2"],
                    "command": "python -m unittest tests.example",
                },
                {
                    "id": "V2",
                    "kind": "semantic",
                    "acceptance_ids": ["A1"],
                    "criterion": "Inspect implementation against feature behavior",
                },
            ],
        },
        "routing": {
            "execution_profile": "auto",
            "review_profile": "auto",
            "execution_profile_override_reason": None,
            "review_profile_override_reason": None,
            "resolved_execution": {
                "profile": "coding-standard",
                "backend": "claude-code",
                "model": "glm-5.2[1M]",
                "effort": "medium",
                "preflight": {
                    "status": "pass",
                    "command": "python tools/route_preflight.py --purpose execute --complexity STANDARD --risk MEDIUM",
                    "exit_code": 0,
                    "evidence": "execution route preflight passed",
                },
            },
            "resolved_review": {
                "profile": "review-standard",
                "backend": "codex",
                "model": "gpt-5.6-terra",
                "effort": "high",
                "preflight": {
                    "status": "pass",
                    "command": "python tools/route_preflight.py --purpose review --complexity STANDARD --risk MEDIUM --worker-backend claude-code",
                    "exit_code": 0,
                    "evidence": "review route preflight passed",
                },
            },
        },
        "retry": {
            "attempt_number": 1,
            "max_retries": 2,
            "same_fingerprint_failures": 0,
            "fingerprint": None,
        },
        "stop_conditions": ["Stop on permission or scope conflict"],
        "handoff": {
            "project_controller": "gpt-taskboard",
            "return_to": "task-board",
        },
    }


def valid_result():
    return {
        "schema_version": "1.4",
        "task_id": "P1-T01",
        "task_revision": 1,
        "attempt_id": "P1-T01-r1-a1",
        "status": "READY_FOR_REVIEW",
        "workspace": {
            "project_root": r"E:\temp\example",
            "baseline": {"kind": "git", "ref": "abc123"},
        },
        "delivery": {
            "branch": "codex/p1-t01",
            "commit": "def456",
            "worktree": r"E:\temp\example-p1-t01",
            "result_artifact": None,
        },
        "worker": {
            "status": "COMPLETED",
            "role": "worker",
            "profile": "coding-standard",
            "backend": "claude-code",
            "model": "glm-5.2[1M]",
            "effort": "medium",
            "execution_mode": "delegated",
            "override_reason": None,
            "session": "worker-session-1",
            "invocation": {
                "command": "claude -p --model glm-5.2[1M] --effort medium task.md",
                "exit_code": 0,
                "evidence": "worker-session-1 completed",
            },
        },
        "changed_paths": [
            "src/example/main.py",
            "tests/example/test_main.py",
        ],
        "verification": {
            "mode": "mixed",
            "result": "PASS",
            "checks": [
                {
                    "id": "V1",
                    "kind": "command",
                    "command": "python -m unittest tests.example",
                    "exit_code": 0,
                    "evidence": "2 tests passed",
                },
                {
                    "id": "V2",
                    "kind": "semantic",
                    "conclusion": "Implementation satisfies feature behavior",
                    "evidence": "Reviewed src/example/main.py",
                },
            ],
        },
        "failure": {
            "fingerprint": None,
            "category": None,
            "same_fingerprint_failures": 0,
            "error_code": None,
        },
        "review": {
            "status": "PENDING",
            "role": "reviewer",
            "profile": "review-standard",
            "reviewer_type": "model",
            "backend": None,
            "model": None,
            "effort": None,
            "session": None,
            "reviewer_id": None,
            "review_revision": None,
            "independence_evidence": None,
            "invocation": None,
            "evidence": [],
        },
        "project_integration": {
            "status": "NOT_EVALUATED",
            "main_ref": None,
            "evidence": [],
        },
        "remaining_risks": [],
        "handoff_notes": [],
    }


def complete_model_review(result, *, session="review-session-2"):
    result["status"] = "REVIEW_PASSED"
    result["review"].update(
        {
            "status": "PASS",
            "backend": "codex",
            "model": "gpt-5.6-terra",
            "effort": "high",
            "session": session,
            "review_revision": 1,
            "independence_evidence": "Separate reviewer process/session",
            "invocation": {
                "command": "codex exec -m gpt-5.6-terra review",
                "exit_code": 0,
                "evidence": f"{session} completed",
            },
            "evidence": ["review checks passed"],
        }
    )


class ExecutionContractValidationTest(unittest.TestCase):
    def setUp(self):
        self.request = valid_request()
        self.result = valid_result()
        validate_request(self.request)
        validate_result(self.result)
        validate_pair(self.request, self.result)

    def test_valid_actual_pair(self):
        validate_request(self.request)
        validate_result(self.result)
        validate_pair(self.request, self.result)

    def test_raw_templates_are_structure_only_not_actual_results(self):
        root = Path(__file__).resolve().parents[1]
        request = yaml.safe_load(
            (root / "ai-development-workflow-v1/templates/EXECUTION_REQUEST.yaml").read_text(
                encoding="utf-8"
            )
        )
        result = yaml.safe_load(
            (root / "ai-development-workflow-v1/templates/EXECUTION_RESULT.yaml").read_text(
                encoding="utf-8"
            )
        )
        validate_request(request, template_mode=True)
        validate_result(result, template_mode=True)
        validate_pair(request, result)
        with self.assertRaisesRegex(ValueError, "placeholder"):
            validate_request(request)
        with self.assertRaisesRegex(ValueError, "placeholder"):
            validate_result(result)

    def test_placeholder_rejected_in_actual_mode(self):
        self.request["objective"] = "<OBJECTIVE>"
        with self.assertRaisesRegex(ValueError, "placeholder"):
            validate_request(self.request)

    def test_plan_gate_must_be_approved_or_not_required(self):
        self.request["governance"]["project_start_gate"]["status"] = "PENDING"
        with self.assertRaisesRegex(ValueError, "APPROVED or NOT_REQUIRED"):
            validate_request(self.request)

    def test_resolved_worker_route_must_match_router(self):
        self.request["routing"]["resolved_execution"]["model"] = "gpt-5.6-sol"
        with self.assertRaisesRegex(ValueError, "route mismatch"):
            validate_request(self.request)

    def test_route_preflight_must_pass(self):
        self.request["routing"]["resolved_execution"]["preflight"]["exit_code"] = 1
        with self.assertRaisesRegex(ValueError, "expected 0"):
            validate_request(self.request)

    def test_worker_must_match_resolved_route(self):
        self.result["worker"]["model"] = "glm-5.3[1M]"
        with self.assertRaisesRegex(ValueError, "resolved execution route"):
            validate_pair(self.request, self.result)

    def test_worker_requires_real_invocation_evidence(self):
        self.result["worker"]["invocation"] = None
        with self.assertRaisesRegex(ValueError, "invocation"):
            validate_result(self.result)

    def test_delegated_worker_cannot_reuse_controller_session(self):
        self.result["worker"]["session"] = "controller-session-1"
        with self.assertRaisesRegex(ValueError, "must differ from controller"):
            validate_pair(self.request, self.result)

    def test_controller_override_requires_explicit_authorization(self):
        self.result["worker"]["execution_mode"] = "controller_override"
        self.result["worker"]["override_reason"] = "User explicitly requested controller implementation."
        with self.assertRaisesRegex(ValueError, "not authorized"):
            validate_pair(self.request, self.result)

    def test_controller_override_is_allowed_only_with_matching_reason(self):
        reason = "User explicitly requested controller implementation."
        self.request["governance"]["controller_worker_override"] = {
            "allowed": True,
            "reason": reason,
        }
        self.result["worker"]["execution_mode"] = "controller_override"
        self.result["worker"]["override_reason"] = reason
        validate_request(self.request)
        validate_result(self.result)
        validate_pair(self.request, self.result)

    def test_acceptance_must_be_covered_by_required_check(self):
        self.request["validation"]["required_checks"][1]["acceptance_ids"] = ["A2"]
        with self.assertRaisesRegex(ValueError, "without required verification"):
            validate_request(self.request)

    def test_missing_required_check_rejected(self):
        self.result["verification"]["checks"] = [self.result["verification"]["checks"][0]]
        with self.assertRaisesRegex(ValueError, "missing required checks"):
            validate_pair(self.request, self.result)

    def test_changed_path_outside_allowed_scope_rejected(self):
        self.result["changed_paths"].append("docs/unrelated.md")
        with self.assertRaisesRegex(ValueError, "outside allowed scope"):
            validate_pair(self.request, self.result)

    def test_forbidden_changed_path_rejected(self):
        self.result["changed_paths"].append("src/example/secrets/token.txt")
        with self.assertRaisesRegex(ValueError, "forbidden path"):
            validate_pair(self.request, self.result)

    def test_review_passed_requires_independent_model_session(self):
        complete_model_review(self.result, session="worker-session-1")
        with self.assertRaisesRegex(ValueError, "must differ"):
            validate_result(self.result)

    def test_review_passed_accepts_independent_routed_model(self):
        complete_model_review(self.result)
        validate_result(self.result)
        validate_pair(self.request, self.result)

    def test_review_must_match_resolved_review_route(self):
        complete_model_review(self.result)
        self.result["review"]["model"] = "gpt-5.6-sol"
        validate_result(self.result)
        with self.assertRaisesRegex(ValueError, "resolved review route"):
            validate_pair(self.request, self.result)

    def test_review_backend_fallback_route_passes_actual_validation(self):
        routing = self.request["routing"]
        reason = "Codex runtime quota exhausted after review started; backend unavailable."
        routing["review_excluded_backends"] = ["codex"]
        routing["review_fallback_reason"] = reason
        routing["resolved_review"].update(
            {
                "backend": "claude-code",
                "model": "glm-5.3[1M]",
                "preflight": {
                    "status": "pass",
                    "command": (
                        "python tools/route_preflight.py --purpose review --complexity STANDARD "
                        "--risk MEDIUM --worker-backend claude-code "
                        f'--exclude-backend codex --fallback-reason "{reason}"'
                    ),
                    "exit_code": 0,
                    "evidence": "review fallback route preflight passed",
                },
            }
        )
        validate_request(self.request)
        validate_result(self.result)
        validate_pair(self.request, self.result)

    def test_review_backend_fallback_still_requires_matching_resolved_route(self):
        self.request["routing"]["review_excluded_backends"] = ["codex"]
        self.request["routing"]["review_fallback_reason"] = (
            "Codex runtime quota exhausted after review started."
        )
        with self.assertRaisesRegex(ValueError, "route mismatch"):
            validate_request(self.request)

    def test_review_backend_exclusion_without_reason_fails(self):
        self.request["routing"]["review_excluded_backends"] = ["codex"]
        with self.assertRaisesRegex(ValueError, "review_fallback_reason"):
            validate_request(self.request)

    def test_review_requires_invocation_evidence(self):
        complete_model_review(self.result)
        self.result["review"]["invocation"] = None
        with self.assertRaisesRegex(ValueError, "invocation"):
            validate_result(self.result)

    def test_review_passed_accepts_human_reviewer(self):
        self.result["status"] = "REVIEW_PASSED"
        self.result["review"].update(
            {
                "status": "PASS",
                "reviewer_type": "human",
                "backend": None,
                "model": None,
                "effort": None,
                "session": None,
                "reviewer_id": "human-reviewer-42",
                "review_revision": 1,
                "independence_evidence": "Recorded human approval reference",
                "invocation": None,
                "evidence": ["approval-record-42"],
            }
        )
        validate_result(self.result)
        validate_pair(self.request, self.result)

    def test_failed_result_requires_fingerprint(self):
        self.result["status"] = "FAILED"
        self.result["worker"]["status"] = "FAILED"
        self.result["verification"]["result"] = "FAIL"
        self.result["failure"].update(
            {
                "fingerprint": "",
                "category": "implementation defect",
                "error_code": "TEST_FAILED",
            }
        )
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            validate_result(self.result)

    def test_execution_result_cannot_claim_project_integration(self):
        self.result["project_integration"]["status"] = "INTEGRATED"
        with self.assertRaisesRegex(ValueError, "NOT_EVALUATED"):
            validate_result(self.result)

    def test_attempt_limit_is_initial_plus_retries(self):
        self.request["retry"]["attempt_number"] = 4
        with self.assertRaisesRegex(ValueError, "initial attempt"):
            validate_request(self.request)


if __name__ == "__main__":
    unittest.main()
