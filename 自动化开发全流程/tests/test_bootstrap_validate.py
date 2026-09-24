import copy
import contextlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from tools.bootstrap_validate import validate

ROOT = Path(__file__).resolve().parents[1]


class BootstrapValidationTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        shutil.copytree(ROOT / ".uads", self.root / ".uads")
        for name in ("SYSTEM_SPEC_V1_REV2.md", "IMPLEMENTATION_PLAN.md", "PHASE_0_START.md"):
            shutil.copyfile(ROOT / name, self.root / name)
        shutil.copytree(ROOT / "ai-development-workflow-v1", self.root / "ai-development-workflow-v1")
        (self.root / "docs").mkdir()
        shutil.copyfile(ROOT / "docs/DEVELOPMENT.md", self.root / "docs/DEVELOPMENT.md")
        self.plan_path = self.root / ".uads/plan.yaml"
        self.plan = yaml.safe_load(self.plan_path.read_text(encoding="utf-8"))
        self.entry = self.plan["phases"][0]["stages"][0]["tasks"][0]
        self.task_path = self.root / self.entry["definition"]
        self.task = yaml.safe_load(self.task_path.read_text(encoding="utf-8"))
        # A valid baseline ensures a negative case fails for the intended reason.
        self.check()

    def check(self):
        with contextlib.redirect_stdout(io.StringIO()):
            validate(self.root)

    def save(self):
        self.plan_path.write_text(yaml.safe_dump(self.plan), encoding="utf-8")
        self.task_path.write_text(yaml.safe_dump(self.task), encoding="utf-8")

    def test_current_seed(self):
        self.check()

    def test_pinned_fields(self):
        original = copy.deepcopy(self.task)
        for field, value, reason in [
            ("revision", 2, "revision mismatch"),
            ("objective", "different objective", "objective mismatch"),
            ("dependencies", ["missing"], "dependencies mismatch"),
            ("retry_budget", {"run": 1, "task": 99, "stage": 4}, "retry budget mismatch"),
            ("schema_version", "2.0", "schema_version mismatch"),
        ]:
            with self.subTest(field=field):
                self.task = copy.deepcopy(original)
                self.task[field] = value
                self.save()
                with self.assertRaisesRegex(ValueError, reason):
                    self.check()

    def test_graph_closure_and_cycle(self):
        for dependencies, reason in [(["missing"], "dependency closure"), ([self.entry["id"]], "dependency cycle")]:
            with self.subTest(dependencies=dependencies):
                self.entry["dependencies"] = dependencies
                self.task["dependencies"] = dependencies
                self.save()
                with self.assertRaisesRegex(ValueError, reason):
                    self.check()

    def test_duplicate_ids(self):
        original = copy.deepcopy(self.plan)
        for kind in ("phase", "stage", "task"):
            with self.subTest(kind=kind):
                self.plan = copy.deepcopy(original)
                if kind == "phase":
                    self.plan["phases"][1]["id"] = self.plan["phases"][0]["id"]
                elif kind == "stage":
                    self.plan["phases"][0]["stages"][1]["id"] = self.plan["phases"][0]["stages"][0]["id"]
                else:
                    tasks = self.plan["phases"][0]["stages"][0]["tasks"]
                    tasks.append(copy.deepcopy(tasks[0]))
                self.save()
                with self.assertRaisesRegex(ValueError, f"duplicate {kind} id"):
                    self.check()

    def test_plan_shape(self):
        original = copy.deepcopy(self.plan)
        for phases in ([], [None], [{"id": "P00", "stages": []}]):
            with self.subTest(phases=phases):
                self.plan = copy.deepcopy(original)
                self.plan["phases"] = phases
                self.save()
                with self.assertRaises(ValueError):
                    self.check()

    def test_booleans_are_not_integers(self):
        self.entry["revision"] = True
        self.save()
        with self.assertRaisesRegex(ValueError, "plan revision"):
            self.check()
        self.entry["revision"] = 1
        self.entry["retry_budget"]["run"] = True
        self.save()
        with self.assertRaisesRegex(ValueError, "plan retry_budget"):
            self.check()

    def test_scope_paths(self):
        for path, reason in [(str(self.root / "src"), "absolute path"), ("../outside", "escapes repository"), (".", "repository-wide")]:
            with self.subTest(path=path):
                self.task["scope"]["include"] = [path]
                self.task["allowed_changes"]["paths"] = [path]
                self.save()
                with self.assertRaisesRegex(ValueError, reason):
                    self.check()
        self.task["scope"] = {}
        self.save()
        with self.assertRaisesRegex(ValueError, "scope requires"):
            self.check()

    def test_missing_and_external_inputs(self):
        for path, reason in [("missing.md", "missing input"), ("../outside.md", "escapes repository")]:
            with self.subTest(path=path):
                self.task["inputs"] = [path]
                self.save()
                with self.assertRaisesRegex(ValueError, reason):
                    self.check()

    def test_duplicate_yaml_keys(self):
        with self.task_path.open("a", encoding="utf-8") as stream:
            stream.write("\nrevision: 99\n")
        with self.assertRaisesRegex(yaml.YAMLError, "duplicate key"):
            self.check()

    def test_definition_paths(self):
        for path, reason in [(".uads/tasks/missing.yaml", "does not exist"), ("../outside.yaml", "escapes repository")]:
            with self.subTest(path=path):
                self.entry["definition"] = path
                self.save()
                with self.assertRaisesRegex(ValueError, reason):
                    self.check()
