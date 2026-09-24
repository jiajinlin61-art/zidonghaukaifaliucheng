import json
import multiprocessing
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.coordinator_lock import (
    CoordinatorLockError,
    acquire_lock,
    break_lock,
    coordinator_state_dir,
    lock_status,
    paths,
    release_lock,
)


def _concurrent_acquire(root: str, owner: str, claim_id: str, start, queue):
    start.wait()
    try:
        result = acquire_lock(Path(root), owner=owner, claim_id=claim_id)
        queue.put((owner, result["status"]))
    except CoordinatorLockError as error:
        queue.put((owner, "rejected:" + str(error)))


class CoordinatorLockTest(unittest.TestCase):
    def test_acquire_and_release(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertEqual(
                acquire_lock(root, owner="agent-a", claim_id="claim-a")["status"],
                "acquired",
            )
            self.assertEqual(lock_status(root)["status"], "locked")
            self.assertEqual(
                release_lock(root, claim_id="claim-a")["status"],
                "released",
            )
            self.assertEqual(lock_status(root)["status"], "unlocked")

    def test_same_claim_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            acquire_lock(root, owner="agent-a", claim_id="claim-a")
            result = acquire_lock(root, owner="agent-a", claim_id="claim-a")
            self.assertEqual(result["status"], "already-held-by-same-claim")

    def test_different_claim_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            acquire_lock(root, owner="agent-a", claim_id="claim-a")
            with self.assertRaisesRegex(CoordinatorLockError, "held by"):
                acquire_lock(root, owner="agent-b", claim_id="claim-b")

    def test_wrong_claim_cannot_release(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            acquire_lock(root, owner="agent-a", claim_id="claim-a")
            with self.assertRaisesRegex(CoordinatorLockError, "mismatch"):
                release_lock(root, claim_id="claim-b")

    def test_old_lock_is_not_auto_stolen(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            acquire_lock(root, owner="agent-a", claim_id="claim-a")
            lock_path, _ = paths(root)
            payload = json.loads(lock_path.read_text(encoding="utf-8"))
            payload["acquired_at"] = "2000-01-01T00:00:00+00:00"
            lock_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(CoordinatorLockError, "held by"):
                acquire_lock(root, owner="agent-b", claim_id="claim-b")

    def test_break_requires_matching_claim_and_reason(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            acquire_lock(root, owner="agent-a", claim_id="claim-a")
            with self.assertRaisesRegex(CoordinatorLockError, "requires a reason"):
                break_lock(root, expected_claim_id="claim-a", reason="")
            with self.assertRaisesRegex(CoordinatorLockError, "mismatch"):
                break_lock(root, expected_claim_id="claim-b", reason="reconciled")
            result = break_lock(
                root,
                expected_claim_id="claim-a",
                reason="TaskBoard and Git reconciled; original coordinator is gone",
            )
            self.assertEqual(result["status"], "broken-after-reconciliation")

    def test_two_concurrent_claims_only_one_acquires(self):
        with tempfile.TemporaryDirectory() as temporary:
            context = multiprocessing.get_context("spawn")
            start = context.Event()
            queue = context.Queue()
            processes = [
                context.Process(
                    target=_concurrent_acquire,
                    args=(temporary, "agent-a", "claim-a", start, queue),
                ),
                context.Process(
                    target=_concurrent_acquire,
                    args=(temporary, "agent-b", "claim-b", start, queue),
                ),
            ]
            for process in processes:
                process.start()
            start.set()
            results = [queue.get(timeout=10) for _ in processes]
            for process in processes:
                process.join(timeout=10)
                self.assertFalse(process.is_alive())

            statuses = [status for _, status in results]
            self.assertEqual(statuses.count("acquired"), 1)
            self.assertEqual(sum(status.startswith("rejected:") for status in statuses), 1)

            current = lock_status(Path(temporary))
            self.assertEqual(current["status"], "locked")
            break_lock(
                Path(temporary),
                expected_claim_id=current["lock"]["claim_id"],
                reason="test cleanup after concurrent acquisition",
            )


    def test_git_worktrees_share_one_coordinator_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "repo"
            worktree = base / "worker-tree"
            root.mkdir()
            subprocess.run(["git", "-C", str(root), "init"], check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", str(root), "config", "user.name", "TaskBoard Test"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "config", "user.email", "taskboard@example.invalid"],
                check=True,
            )
            (root / "README.md").write_text("baseline\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-m", "baseline"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "worktree", "add", "-b", "task/test", str(worktree)],
                check=True,
                capture_output=True,
            )

            self.assertEqual(
                coordinator_state_dir(root).resolve(),
                coordinator_state_dir(worktree).resolve(),
            )
            acquire_lock(root, owner="agent-a", claim_id="claim-a")
            with self.assertRaisesRegex(CoordinatorLockError, "held by"):
                acquire_lock(worktree, owner="agent-b", claim_id="claim-b")
            release_lock(worktree, claim_id="claim-a")
            self.assertEqual(lock_status(root)["status"], "unlocked")


if __name__ == "__main__":
    unittest.main()
