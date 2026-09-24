import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from tools.model_router import DEFAULT_CONFIG, load_config
from tools.route_preflight import (
    canonical_hash,
    preflight_route,
    run_version,
    scrub_sensitive,
)


class RoutePreflightTest(unittest.TestCase):
    def make_config(self):
        return load_config(DEFAULT_CONFIG)

    def write_config(self, config):
        temporary = tempfile.TemporaryDirectory()
        path = Path(temporary.name) / "routing.yaml"
        path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        return temporary, path

    def test_sensitive_values_do_not_affect_fingerprint(self):
        first = {"model": "x", "env": {"AUTH_TOKEN": "one", "BASE_URL": "https://a"}}
        second = {"model": "x", "env": {"AUTH_TOKEN": "two", "BASE_URL": "https://a"}}
        self.assertEqual(canonical_hash(first), canonical_hash(second))
        self.assertNotIn("AUTH_TOKEN", scrub_sensitive(first)["env"])

    def test_non_secret_route_config_change_affects_fingerprint(self):
        first = {"model": "x", "env": {"BASE_URL": "https://a"}}
        second = {"model": "x", "env": {"BASE_URL": "https://b"}}
        self.assertNotEqual(canonical_hash(first), canonical_hash(second))

    def test_preflight_passes_when_version_config_probe_and_freshness_match(self):
        config = self.make_config()
        expected = config["backends"]["claude-code"]["preflight"]["config_fingerprint"]
        temporary, path = self.write_config(config)
        self.addCleanup(temporary.cleanup)
        with patch("tools.route_preflight.run_version", return_value="2.1.278 (Claude Code)"), patch(
            "tools.route_preflight.config_fingerprint", return_value=expected
        ):
            result = preflight_route(
                config_path=path,
                purpose="execute",
                complexity="STANDARD",
                risk="MEDIUM",
            )
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["probe_freshness_check"], "pass")

    def test_preflight_rejects_cli_version_change(self):
        config = self.make_config()
        expected = config["backends"]["claude-code"]["preflight"]["config_fingerprint"]
        temporary, path = self.write_config(config)
        self.addCleanup(temporary.cleanup)
        with patch("tools.route_preflight.run_version", return_value="9.9.9"), patch(
            "tools.route_preflight.config_fingerprint", return_value=expected
        ):
            with self.assertRaisesRegex(ValueError, "CLI version changed"):
                preflight_route(
                    config_path=path,
                    purpose="execute",
                    complexity="STANDARD",
                    risk="MEDIUM",
                )

    def test_preflight_rejects_config_change(self):
        config = self.make_config()
        temporary, path = self.write_config(config)
        self.addCleanup(temporary.cleanup)
        with patch("tools.route_preflight.run_version", return_value="2.1.278 (Claude Code)"), patch(
            "tools.route_preflight.config_fingerprint", return_value="sha256:different"
        ):
            with self.assertRaisesRegex(ValueError, "config fingerprint changed"):
                preflight_route(
                    config_path=path,
                    purpose="execute",
                    complexity="STANDARD",
                    risk="MEDIUM",
                )

    def test_preflight_rejects_model_not_in_probe_record(self):
        config = self.make_config()
        config["backends"]["claude-code"]["preflight"]["probed_models"].remove("glm-5.2[1M]")
        expected = config["backends"]["claude-code"]["preflight"]["config_fingerprint"]
        temporary, path = self.write_config(config)
        self.addCleanup(temporary.cleanup)
        with patch("tools.route_preflight.run_version", return_value="2.1.278 (Claude Code)"), patch(
            "tools.route_preflight.config_fingerprint", return_value=expected
        ):
            with self.assertRaisesRegex(ValueError, "not present in current probed_models"):
                preflight_route(
                    config_path=path,
                    purpose="execute",
                    complexity="STANDARD",
                    risk="MEDIUM",
                )

    def test_preflight_rejects_expired_probe_record(self):
        config = self.make_config()
        config["backends"]["claude-code"]["preflight"]["verified_at"] = "2000-01-01"
        temporary, path = self.write_config(config)
        self.addCleanup(temporary.cleanup)
        with self.assertRaisesRegex(ValueError, "probe record expired"):
            preflight_route(
                config_path=path,
                purpose="execute",
                complexity="STANDARD",
                risk="MEDIUM",
            )

    def test_preflight_checks_selected_fallback_candidate_like_normal_candidate(self):
        config = self.make_config()
        expected = config["backends"]["claude-code"]["preflight"]["config_fingerprint"]
        temporary, path = self.write_config(config)
        self.addCleanup(temporary.cleanup)
        with patch("tools.route_preflight.run_version", return_value="2.1.278 (Claude Code)"), patch(
            "tools.route_preflight.config_fingerprint", return_value=expected
        ):
            result = preflight_route(
                config_path=path,
                purpose="review",
                complexity="COMPLEX",
                risk="HIGH",
                worker_backend="claude-code",
                excluded_backends=["codex"],
                fallback_reason="Codex runtime quota exhausted after review started.",
            )
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["route"]["backend"], "claude-code")
        self.assertEqual(result["route"]["model"], "glm-5.3[1M]")
        self.assertEqual(result["route"]["excluded_backends"], ["codex"])

    def test_preflight_rejects_fallback_when_selected_backend_probe_changed(self):
        config = self.make_config()
        config["backends"]["claude-code"]["preflight"]["probed_models"].remove("glm-5.3[1M]")
        expected = config["backends"]["claude-code"]["preflight"]["config_fingerprint"]
        temporary, path = self.write_config(config)
        self.addCleanup(temporary.cleanup)
        with patch("tools.route_preflight.run_version", return_value="2.1.278 (Claude Code)"), patch(
            "tools.route_preflight.config_fingerprint", return_value=expected
        ):
            with self.assertRaisesRegex(ValueError, "not present in current probed_models"):
                preflight_route(
                    config_path=path,
                    purpose="review",
                    complexity="COMPLEX",
                    risk="HIGH",
                    worker_backend="claude-code",
                    excluded_backends=["codex"],
                    fallback_reason="Codex runtime quota exhausted after review started.",
                )

    def test_missing_backend_executable_is_rejected(self):
        with patch("tools.route_preflight.shutil.which", return_value=None):
            with self.assertRaisesRegex(ValueError, "executable not found"):
                run_version("missing-backend")


if __name__ == "__main__":
    unittest.main()
