# Phase 0 Start

## Scope

Start only Phase 0. Do not begin Phase 1 and do not modify the HR project.

## First executable Stage

`P00-S01 — Repository and development contract`

## First Task

`P00-S01-T03 — Integrate product design lifecycle and review gates`

Environment setup and exact PowerShell commands are in `docs/DEVELOPMENT.md`. Below, `python` means the project `.venv` interpreter.

## Preconditions

- Read `SYSTEM_SPEC_V1_REV2.md` and `IMPLEMENTATION_PLAN.md`.
- Confirm the working tree and target repository are identified; preserve existing user changes.
- Run `python tools/bootstrap_validate.py` against `.uads/plan.yaml` and `.uads/tasks/`.
- Confirm the HR project is outside the allowed change scope.

## Execution

Execute `.uads/tasks/P00-S01-T03.yaml` first, as explicitly authorized by the user, through the documented, human-operated stage-gated workflow. This task remains inside Phase 0 and must not mark P00-S01-T01/T02 or Phase 0 complete. After its Task Gate passes, the next task is P00-S01-T01. No executor is assumed to exist yet.

Suggested gate commands after the Task:

```text
python tools/check_tests.py
python -c "import uads"
```

Use the repository's configured Python command if it differs. Record command output, changed paths, and the Task result artifact.

## Exit

The Stage may advance only when the bootstrap checker, non-empty test discovery gate, minimal import smoke test, completion signal, and independent review pass. Otherwise stop at `NEEDS_HUMAN` or revise the Task explicitly. After P00-S01-T03 passes, the next Task is `P00-S01-T01`; later tasks remain subject to their declared dependencies and the Phase 0 Stage Gate. Phase 1 is not an exit from this document. The formal executor and validation runtime may replace these manual checks only after they pass their own acceptance criteria.
