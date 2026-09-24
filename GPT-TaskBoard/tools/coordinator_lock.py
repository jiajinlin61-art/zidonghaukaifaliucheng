"""Atomic project-level coordinator lock for GPT-TaskBoard claim transactions.

The lock protects only the short READY -> IN_PROGRESS coordination critical section.
It is not a task-execution lease and it is intentionally not auto-stolen by age.

A crashed coordinator leaves the lock in place. Recovery must reconcile TaskBoard/Git
state and explicitly release or break the same claim id before another claim starts.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from typing import Any

LOCK_DIR = "gpt-taskboard"
LOCK_FILE = "coordinator.lock.json"
EVENT_FILE = "coordinator-lock-events.jsonl"
SCHEMA_VERSION = 1


class CoordinatorLockError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def coordinator_state_dir(project_root: Path) -> Path:
    root = project_root.resolve()
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--git-common-dir"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if completed.returncode == 0:
        raw = completed.stdout.strip()
        if raw:
            git_dir = Path(raw)
            if not git_dir.is_absolute():
                git_dir = (root / git_dir).resolve()
            return git_dir / LOCK_DIR
    return root / ".gpt-taskboard"


def paths(project_root: Path) -> tuple[Path, Path]:
    state_dir = coordinator_state_dir(project_root)
    return state_dir / LOCK_FILE, state_dir / EVENT_FILE


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise CoordinatorLockError("coordinator lock does not exist") from error
    except json.JSONDecodeError as error:
        raise CoordinatorLockError("coordinator lock is malformed; manual reconciliation required") from error
    if not isinstance(value, dict):
        raise CoordinatorLockError("coordinator lock is malformed; expected object")
    return value


def append_event(event_path: Path, payload: dict[str, Any]) -> None:
    event_path.parent.mkdir(parents=True, exist_ok=True)
    with event_path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def acquire_lock(project_root: Path, *, owner: str, claim_id: str) -> dict[str, Any]:
    root = project_root.resolve()
    lock_path, event_path = paths(root)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "owner": owner,
        "claim_id": claim_id,
        "acquired_at": utc_now(),
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "purpose": "task-claim-transaction",
    }

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(lock_path, flags, 0o600)
    except FileExistsError:
        current = read_json(lock_path)
        if current.get("claim_id") == claim_id and current.get("owner") == owner:
            return {"status": "already-held-by-same-claim", "lock": current}
        raise CoordinatorLockError(
            "coordinator lock held by "
            f"owner={current.get('owner')!r} claim_id={current.get('claim_id')!r}; "
            "do not start a second claim transaction"
        )

    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass
        raise

    append_event(
        event_path,
        {
            "event": "acquired",
            "at": payload["acquired_at"],
            "owner": owner,
            "claim_id": claim_id,
            "pid": payload["pid"],
            "host": payload["host"],
        },
    )
    return {"status": "acquired", "lock": payload}


def release_lock(project_root: Path, *, claim_id: str) -> dict[str, Any]:
    root = project_root.resolve()
    lock_path, event_path = paths(root)
    current = read_json(lock_path)
    if current.get("claim_id") != claim_id:
        raise CoordinatorLockError(
            f"claim id mismatch: lock belongs to {current.get('claim_id')!r}"
        )
    lock_path.unlink()
    append_event(
        event_path,
        {
            "event": "released",
            "at": utc_now(),
            "owner": current.get("owner"),
            "claim_id": claim_id,
        },
    )
    return {"status": "released", "claim_id": claim_id}


def break_lock(project_root: Path, *, expected_claim_id: str, reason: str) -> dict[str, Any]:
    if not reason.strip():
        raise CoordinatorLockError("breaking a coordinator lock requires a reason")
    root = project_root.resolve()
    lock_path, event_path = paths(root)
    current = read_json(lock_path)
    if current.get("claim_id") != expected_claim_id:
        raise CoordinatorLockError(
            f"claim id mismatch: lock belongs to {current.get('claim_id')!r}"
        )
    lock_path.unlink()
    append_event(
        event_path,
        {
            "event": "broken-after-reconciliation",
            "at": utc_now(),
            "owner": current.get("owner"),
            "claim_id": expected_claim_id,
            "reason": reason.strip(),
        },
    )
    return {
        "status": "broken-after-reconciliation",
        "claim_id": expected_claim_id,
        "reason": reason.strip(),
    }


def lock_status(project_root: Path) -> dict[str, Any]:
    root = project_root.resolve()
    lock_path, _ = paths(root)
    if not lock_path.exists():
        return {"status": "unlocked"}
    return {"status": "locked", "lock": read_json(lock_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="action", required=True)

    acquire = subparsers.add_parser("acquire")
    acquire.add_argument("--owner", required=True)
    acquire.add_argument("--claim-id", required=True)

    release = subparsers.add_parser("release")
    release.add_argument("--claim-id", required=True)

    break_parser = subparsers.add_parser("break")
    break_parser.add_argument("--expected-claim-id", required=True)
    break_parser.add_argument("--reason", required=True)

    subparsers.add_parser("status")

    args = parser.parse_args()
    try:
        if args.action == "acquire":
            result = acquire_lock(args.project_root, owner=args.owner, claim_id=args.claim_id)
        elif args.action == "release":
            result = release_lock(args.project_root, claim_id=args.claim_id)
        elif args.action == "break":
            result = break_lock(
                args.project_root,
                expected_claim_id=args.expected_claim_id,
                reason=args.reason,
            )
        else:
            result = lock_status(args.project_root)
    except (OSError, CoordinatorLockError) as error:
        print(f"coordinator lock failed: {error}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
