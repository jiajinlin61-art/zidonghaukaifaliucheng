"""Validate the bootstrap plan and pinned task definitions with a real YAML parser."""
from __future__ import annotations

import argparse
from pathlib import Path, PureWindowsPath
import sys

import yaml
from yaml.constructor import ConstructorError
from yaml.loader import SafeLoader


REQUIRED_TASK_KEYS = {"schema_version", "task_id", "revision", "objective", "dependencies", "retry_budget"}


class UniqueLoader(SafeLoader):
    """Safe YAML loader that fails closed on duplicate mapping keys."""


def construct_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ConstructorError(None, None, "mapping keys must be strings", key_node.start_mark)
        if key in mapping:
            raise ConstructorError("while constructing a mapping", node.start_mark, f"duplicate key {key!r}", key_node.start_mark)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)


def fail(message: str) -> None:
    raise ValueError(message)


def load(path: Path):
    with path.open(encoding="utf-8") as stream:
        value = yaml.load(stream, Loader=UniqueLoader)
    if not isinstance(value, dict):
        fail(f"{path}: expected a mapping")
    return value


def relative_paths(value, root: Path, label: str, *, allow_empty=False) -> None:
    if not isinstance(value, list) or (not value and not allow_empty) or not all(isinstance(item, str) and item.strip() for item in value):
        fail(f"{label}: expected a list of paths")
    for item in value:
        raw = Path(item)
        windows = PureWindowsPath(item)
        if raw.is_absolute() or windows.drive or windows.root:
            fail(f"{label}: absolute path is forbidden: {item}")
        path = (root / raw).resolve()
        if path == root.resolve():
            fail(f"{label}: repository-wide path is forbidden: {item}")
        if root.resolve() not in path.parents and path != root.resolve():
            fail(f"{label}: path escapes repository: {item}")


def positive_integer(value, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        fail(f"{label}: expected a positive integer")


def validate(root: Path) -> None:
    root = root.resolve()
    plan_path = root / ".uads" / "plan.yaml"
    plan = load(plan_path)
    if plan.get("schema_version") != "1.0":
        fail("unsupported plan schema_version")
    if not isinstance(plan.get("phases"), list) or not plan["phases"]:
        fail("plan must contain non-empty phases")
    entries = []
    phase_ids, stage_ids = set(), set()
    def identified(node, label):
        if not isinstance(node, dict) or not isinstance(node.get("id"), str) or not node["id"].strip():
            fail(f"{label}: expected a mapping with a non-empty id")
        return node["id"]

    for phase in plan.get("phases", []):
        identified(phase, "phase")
        if phase.get("id") in phase_ids:
            fail(f"duplicate phase id {phase.get('id')}")
        phase_ids.add(phase.get("id"))
        if not isinstance(phase.get("stages"), list) or not phase["stages"]:
            fail(f"{phase['id']}: stages must be non-empty")
        for stage in phase.get("stages", []):
            identified(stage, "stage")
            if stage.get("id") in stage_ids:
                fail(f"duplicate stage id {stage.get('id')}")
            stage_ids.add(stage.get("id"))
            if not isinstance(stage.get("tasks"), list) or not stage["tasks"]:
                fail(f"{stage['id']}: tasks must be non-empty")
            for entry in stage.get("tasks", []):
                identified(entry, "task")
                entries.append(entry)
    ids = [entry.get("id") for entry in entries]
    if not entries:
        fail("plan must contain at least one task")
    if len(ids) != len(set(ids)):
        fail("duplicate task id")
    if any(not isinstance(task_id, str) or not task_id for task_id in ids):
        fail("every plan task needs an id")
    known = set(ids)
    dependencies = {}
    for entry in entries:
        positive_integer(entry.get("revision"), f"{entry.get('id')}: plan revision")
        if not isinstance(entry.get("retry_budget"), dict):
            fail(f"{entry.get('id')}: plan retry_budget must be a mapping")
        for value in entry["retry_budget"].values():
            positive_integer(value, f"{entry['id']}: plan retry_budget")
        definition_ref = entry.get("definition")
        relative_paths([definition_ref], root, f"{entry['id']}: definition")
        definition = (root / definition_ref).resolve()
        if root.resolve() not in definition.parents or not definition.is_file():
            fail(f"{entry['id']}: definition escapes root or does not exist")
        task = load(definition)
        if task.get("schema_version") != plan["schema_version"]:
            fail(f"{entry['id']}: schema_version mismatch")
        missing = REQUIRED_TASK_KEYS - task.keys()
        if missing:
            fail(f"{entry['id']}: missing {sorted(missing)}")
        if task.get("task_id") != entry["id"]:
            fail(f"{entry['id']}: task_id mismatch")
        if task.get("revision") != entry.get("revision"):
            fail(f"{entry['id']}: revision mismatch")
        if task.get("objective") != entry.get("objective"):
            fail(f"{entry['id']}: objective mismatch")
        if task.get("dependencies") != entry.get("dependencies"):
            fail(f"{entry['id']}: dependencies mismatch")
        if task.get("retry_budget") != entry.get("retry_budget"):
            fail(f"{entry['id']}: retry budget mismatch")
        positive_integer(task["revision"], f"{entry['id']}: revision")
        if not isinstance(task["objective"], str) or not task["objective"].strip():
            fail(f"{entry['id']}: objective must be non-empty")
        if not isinstance(task["dependencies"], list) or not all(isinstance(dep, str) for dep in task["dependencies"]):
            fail(f"{entry['id']}: dependencies must be a list")
        budget = task["retry_budget"]
        if not isinstance(budget, dict) or set(budget) != {"task", "stage", "run"}:
            fail(f"{entry['id']}: retry_budget must contain task/stage/run")
        for name, value in budget.items():
            positive_integer(value, f"{entry['id']}: retry_budget.{name}")
        scope = task.get("scope")
        if not isinstance(scope, dict) or "include" not in scope or "exclude" not in scope:
            fail(f"{entry['id']}: scope requires include and exclude")
        relative_paths(scope["include"], root, f"{entry['id']}: scope.include")
        relative_paths(scope["exclude"], root, f"{entry['id']}: scope.exclude", allow_empty=True)
        allowed = task.get("allowed_changes")
        if not isinstance(allowed, dict) or "paths" not in allowed:
            fail(f"{entry['id']}: allowed_changes.paths is required")
        relative_paths(allowed["paths"], root, f"{entry['id']}: allowed_changes.paths")
        if allowed["paths"] != scope["include"]:
            fail(f"{entry['id']}: allowed_changes.paths must equal scope.include")
        for include in scope["include"]:
            if any((root / include).resolve().is_relative_to((root / exclude).resolve()) for exclude in scope["exclude"]):
                fail(f"{entry['id']}: included path is excluded: {include}")
        relative_paths(task.get("inputs"), root, f"{entry['id']}: inputs")
        for input_path in task["inputs"]:
            if not (root / input_path).is_file():
                fail(f"{entry['id']}: missing input {input_path}")
        dependencies[entry["id"]] = task["dependencies"]
        if any(dep not in known for dep in task["dependencies"]):
            fail(f"{entry['id']}: dependency closure failure")
    visiting, visited = set(), set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            fail(f"dependency cycle at {task_id}")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in dependencies[task_id]:
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in ids:
        visit(task_id)
    print(f"validated {len(ids)} tasks, {len(visited)} dependency nodes")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        validate(args.root.resolve())
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"bootstrap validation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
