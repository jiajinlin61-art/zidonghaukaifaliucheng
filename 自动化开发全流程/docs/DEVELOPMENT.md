# UADS Development Contract

Supported Python: 3.11 or newer. This workspace uses `D:\install\work\Python313\python.exe` and its project-local `.venv`.

Run from the project root in PowerShell (create the environment only if missing):

```powershell
& 'D:\install\work\Python313\python.exe' -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -e '.[dev]'
& '.\.venv\Scripts\python.exe' tools/bootstrap_validate.py
& '.\.venv\Scripts\python.exe' tools/check_tests.py
& '.\.venv\Scripts\python.exe' -c "import uads; print(uads.__version__)"
```

The editable installation makes the `src/` package importable. `tools/check_tests.py` uses unittest and rejects zero collected tests; plain discovery is not the acceptance gate. Test fixtures run in temporary directories.

PyYAML is a development-only dependency for real YAML parsing, including duplicate-key rejection. The bootstrap checker validates non-empty plan structure, unique IDs, relative in-root paths, input existence, dependency closure/cycles and pinned definition fields. It is not the full P01 schema validator or a runtime filesystem sandbox. New output paths may not exist yet; input and definition files must exist.

`scope.include` and `scope.exclude` contain repository-relative paths; directory paths cover descendants and exclusions win. Top-level `allowed_changes.paths` equals `scope.include` in this seed. `scope_description` and `non_goals` preserve the original human constraints. Future module paths are planned boundaries, not evidence that those modules exist. Tests and runtime examples must write artifacts in temporary repositories.

The 35 task files remain unpublished revision-1 bootstrap seeds: no canonical publication hashes or runtime event history are present. This correction normalizes those seeds without asserting any runtime task completed. Once published, definitions are immutable and changes require a new revision. Historical bootstrap validation notes are not part of the active source of truth; current contracts and real validation results are authoritative.

Phase-gated work records changed paths and actual verification output. A quality gate is not an extra permission request; existing authorization and explicit human stop points remain authoritative. This directory currently has no Git repository, so do not invent HEAD or a clean-worktree claim.
