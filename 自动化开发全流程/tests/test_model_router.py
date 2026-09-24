import tempfile
import unittest
from pathlib import Path

import yaml

from tools.model_router import DEFAULT_CONFIG, load_config, resolve_route


class ModelRouterTest(unittest.TestCase):
    def route(self, **kwargs):
        return resolve_route(config_path=DEFAULT_CONFIG, **kwargs)

    def test_trivial_low_cost_route_uses_glm51(self):
        route = self.route(purpose="execute", complexity="TRIVIAL", risk="LOW")
        self.assertEqual(route["profile"], "coding-economy")
        self.assertEqual(route["backend"], "claude-code")
        self.assertEqual(route["model"], "glm-5.1")

    def test_simple_fast_route_uses_glm53_flash(self):
        route = self.route(purpose="execute", complexity="SIMPLE", risk="LOW")
        self.assertEqual(route["profile"], "coding-fast")
        self.assertEqual(route["model"], "glm-5.3-flash[1M]")

    def test_standard_route_uses_glm52(self):
        route = self.route(purpose="execute", complexity="STANDARD", risk="MEDIUM")
        self.assertEqual(route["profile"], "coding-standard")
        self.assertEqual(route["model"], "glm-5.2[1M]")

    def test_complex_route_uses_glm53(self):
        route = self.route(purpose="execute", complexity="COMPLEX", risk="MEDIUM")
        self.assertEqual(route["profile"], "coding-complex")
        self.assertEqual(route["model"], "glm-5.3[1M]")

    def test_high_risk_standard_route_uses_coding_complex(self):
        route = self.route(purpose="execute", complexity="STANDARD", risk="HIGH")
        self.assertEqual(route["profile"], "coding-complex")
        self.assertEqual(route["model"], "glm-5.3[1M]")

    def test_critical_route_uses_sol(self):
        route = self.route(purpose="execute", complexity="CRITICAL", risk="CRITICAL")
        self.assertEqual(route["profile"], "coding-critical")
        self.assertEqual(route["backend"], "codex")
        self.assertEqual(route["model"], "gpt-5.6-sol")

    def test_second_same_failure_escalates(self):
        once = self.route(
            purpose="execute",
            complexity="SIMPLE",
            risk="LOW",
            failure_count=1,
        )
        twice = self.route(
            purpose="execute",
            complexity="SIMPLE",
            risk="LOW",
            failure_count=2,
        )
        self.assertEqual(once["profile"], "coding-fast")
        self.assertEqual(twice["profile"], "coding-standard")

    def test_deep_debug(self):
        route = self.route(purpose="debug", complexity="COMPLEX", risk="MEDIUM")
        self.assertEqual(route["profile"], "debug-deep")
        self.assertEqual(route["model"], "glm-5.3[1M]")

    def test_review_prefers_different_backend(self):
        route = self.route(
            purpose="review",
            complexity="STANDARD",
            risk="MEDIUM",
            worker_backend="claude-code",
        )
        self.assertEqual(route["profile"], "review-standard")
        self.assertEqual(route["backend"], "codex")
        self.assertEqual(route["model"], "gpt-5.6-terra")

    def test_critical_review_uses_sol(self):
        route = self.route(
            purpose="review",
            complexity="STANDARD",
            risk="HIGH",
            worker_backend="claude-code",
        )
        self.assertEqual(route["profile"], "review-critical")
        self.assertEqual(route["model"], "gpt-5.6-sol")

    def test_critical_review_runtime_fallback_selects_configured_fallback(self):
        route = self.route(
            purpose="review",
            complexity="COMPLEX",
            risk="HIGH",
            worker_backend="claude-code",
            excluded_backends=["codex"],
            fallback_reason="Codex runtime quota exhausted after review started.",
        )
        self.assertEqual(route["profile"], "review-critical")
        self.assertEqual(route["backend"], "claude-code")
        self.assertEqual(route["model"], "glm-5.3[1M]")
        self.assertEqual(route["excluded_backends"], ["codex"])
        self.assertIn("quota", route["fallback_reason"])

    def test_backend_exclusion_requires_fallback_reason(self):
        with self.assertRaisesRegex(ValueError, "fallback reason"):
            self.route(
                purpose="review",
                complexity="COMPLEX",
                risk="HIGH",
                excluded_backends=["codex"],
            )

    def test_excluding_all_compatible_backends_fails(self):
        with self.assertRaisesRegex(ValueError, "removed all enabled and verified candidates"):
            self.route(
                purpose="review",
                complexity="COMPLEX",
                risk="HIGH",
                excluded_backends=["codex", "claude-code"],
                fallback_reason="All backends unavailable.",
            )

    def test_visual_route_uses_flash(self):
        route = self.route(
            purpose="execute",
            complexity="STANDARD",
            risk="MEDIUM",
            task_kind="visual",
        )
        self.assertEqual(route["profile"], "visual-coding")
        self.assertEqual(route["model"], "glm-5.3-flash[1M]")

    def test_high_risk_visual_route_does_not_use_flash(self):
        route = self.route(
            purpose="execute",
            complexity="STANDARD",
            risk="HIGH",
            task_kind="visual",
        )
        self.assertEqual(route["profile"], "coding-complex")
        self.assertEqual(route["model"], "glm-5.3[1M]")

    def test_explicit_profile_override_can_upgrade(self):
        route = self.route(
            purpose="execute",
            complexity="TRIVIAL",
            risk="LOW",
            override="coding-complex",
            override_reason="Task touches a fragile legacy integration.",
        )
        self.assertEqual(route["profile"], "coding-complex")
        self.assertEqual(route["model"], "glm-5.3[1M]")
        self.assertIn("fragile", route["override_reason"])

    def test_override_requires_reason(self):
        with self.assertRaisesRegex(ValueError, "override reason"):
            self.route(
                purpose="execute",
                complexity="TRIVIAL",
                risk="LOW",
                override="coding-complex",
            )

    def test_override_cannot_downgrade_critical_task(self):
        with self.assertRaisesRegex(ValueError, "cannot downgrade"):
            self.route(
                purpose="execute",
                complexity="CRITICAL",
                risk="CRITICAL",
                override="coding-economy",
                override_reason="Prefer a cheaper model.",
            )

    def test_override_role_must_match_purpose(self):
        with self.assertRaisesRegex(ValueError, "role mismatch"):
            self.route(
                purpose="review",
                complexity="STANDARD",
                risk="MEDIUM",
                override="coding-critical",
                override_reason="Use a stronger profile.",
            )

    def test_unverified_candidate_is_not_auto_selected(self):
        config = load_config(DEFAULT_CONFIG)
        for candidate in config["profiles"]["coding-standard"]["candidates"]:
            candidate["verification"] = "cli_observed"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "routing.yaml"
            path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "verified candidate"):
                resolve_route(
                    config_path=path,
                    purpose="execute",
                    complexity="STANDARD",
                    risk="MEDIUM",
                )

    def test_required_model_families_are_present(self):
        config = load_config(DEFAULT_CONFIG)
        models = {
            candidate["model"]
            for profile in config["profiles"].values()
            for candidate in profile["candidates"]
        }
        required = {
            "glm-5.1",
            "glm-5.2[1M]",
            "glm-5.3[1M]",
            "glm-5.3-flash[1M]",
            "gpt-5.6-luna",
            "gpt-5.6-terra",
            "gpt-5.6-sol",
        }
        self.assertTrue(required.issubset(models), required - models)


if __name__ == "__main__":
    unittest.main()
