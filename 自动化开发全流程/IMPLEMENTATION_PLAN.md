# Universal AI Development System V1
## Implementation Plan

**Baseline:** `SYSTEM_SPEC_V1_REV2.md` — design baseline; runtime acceptance remains pending
**Execution mode:** one Stage at a time; do not start the next Stage until the current Stage quality gate passes.
**Source of truth:** after Phase 0, `.uads/plan.yaml` and the pinned Task Definition files are authoritative; this document is the human-readable plan.

## Delivery rules

- A Stage is an integration verification boundary. At its end, run its quality gate and record the completion signal. Continue within existing authorization; stop for explicit human checkpoints or unresolved decisions.
- A Task may modify only its declared scope. Every Task produces its own evidence.
- Later Tasks may not paper over a failed earlier gate. A failed gate returns the Stage to `NEEDS_HUMAN` or creates an explicit revision Task.
- The first implementation target is a local, single-process reference implementation. Providers, executors, and persistence adapters remain replaceable.
- Recommended default route: `local-process-executor` + `coding-reasoning` profile + structured `task_result_v1` output.

The task files are unpublished bootstrap seeds; see `docs/DEVELOPMENT.md` for revision/publication rules. Scope paths in the seeds are planned boundaries, not implemented modules.

## Phase map

| Phase | Outcome |
|---|---|
| P00 | Repository skeleton and executable development contract |
| P01 | Schemas, canonicalization, and plan validation |
| P02 | Durable events, materialized state, and transition engine |
| P03 | Scheduling, retries, fingerprints, and human decisions |
| P04 | Context bundles, checkpoints, and run manifests |
| P05 | Route resolution and execution supervision |
| P06 | Result parsing and deterministic/semantic verification |
| P07 | Recovery, security, audit, and end-to-end reference flow |
| P08 | Hardening, documentation, and V1 release gate |

---

## P00 — Foundation

### P00-S01 — Repository and development contract

#### P00-S01-T03 — Integrate product design lifecycle and review gates

- **objective:** Integrate complexity-scaled product design artifacts and two FULL-mode approval gates into the current workflow.
- **scope:** workflow policies, prompts, templates, starter-project guidance, plan gate validator and tests, plus the P00 task plan and evidence.
- **dependencies:** none
- **acceptance criteria:** FAST/STANDARD/FULL share one execution core; FULL has a plan approval and a design-baseline approval before implementation; the validator blocks missing approvals; reviewer routing and session independence are documented and consistent with existing bindings.
- **recommended executor/model profile:** Claude Code / coding-standard
- **quality gate:** focused project-start-gate tests, bootstrap task-plan validation, full non-empty test suite, and independent Review.
- **expected outputs:** updated workflow guidance and templates, schema-compatible Project Start Gate validation, task plan records and verification evidence.
- **completion signal:** `P00-S01-T03.completed` with changed-path list and actual check output.

#### P00-S01-T01 — Create reference implementation layout

- **objective:** Create the minimum package, test, fixture, and `.uads/` layout for the local reference implementation.
- **scope:** `src/`, `tests/`, `.uads/`, `pyproject.toml`, development documentation; no provider integration.
- **dependencies:** P00-S01-T03
- **acceptance criteria:** package imports; test runner starts; required directories are explicit; no runtime behavior is hidden in test fixtures.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** non-empty unittest execution and a minimal import smoke test. Bootstrap plan validation is a separate seed check and is not end-to-end runtime evidence.
- **expected outputs:** repository skeleton; test command; documented supported Python version.
- **completion signal:** `P00-S01-T01.completed` with command output and changed-path list.

#### P00-S01-T02 — Establish coding and evidence conventions

- **objective:** Define the conventions used by later Tasks for schemas, errors, event evidence, and test naming.
- **scope:** project developer documentation and test helpers only.
- **dependencies:** P00-S01-T01
- **acceptance criteria:** conventions cover canonical JSON/YAML inputs, error codes, artifact paths, and quality-gate evidence.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** documentation review against Revision 2 sections 2, 3, 10, 15, and 18.
- **expected outputs:** developer contract and reusable test helpers, if needed.
- **completion signal:** reviewed convention document plus passing helper tests.

### P00-S02 — Executable plan seed

#### P00-S02-T01 — Define initial machine-readable plan

- **objective:** Materialize this plan as `.uads/plan.yaml` with pinned Task Definition paths and dependencies.
- **scope:** `.uads/plan.yaml`, `.uads/tasks/*.yaml`; no scheduler implementation.
- **dependencies:** P00-S01-T02
- **acceptance criteria:** every listed Task has a unique ID, definition path, dependency list, and revision; the graph is acyclic.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** a temporary structural checker proves ID uniqueness, path existence, and dependency closure.
- **expected outputs:** complete plan manifest and initial Task Definition files.
- **completion signal:** plan hash recorded; structural checker passes.

---

## P01 — Contracts and plan validation

### P01-S01 — Canonical schemas

#### P01-S01-T01 — Implement Task Definition schema

- **objective:** Validate immutable Task Definitions, revisions, scope, dependencies, acceptance criteria, and retry budgets.
- **scope:** contract models, schema errors, canonical serialization, unit tests.
- **dependencies:** P00-S02-T01
- **acceptance criteria:** invalid identity, revision, scope, criteria, and budget inputs fail closed; canonical hash is stable.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** schema and canonicalization tests, including reordered mapping keys.
- **expected outputs:** Task Definition validator and canonical hash function.
- **completion signal:** all contract tests pass; hash fixtures are committed.

#### P01-S01-T02 — Implement Runtime State and identity schemas

- **objective:** Validate Runtime State, attempt identity, route identity, checkpoint/result references, and task revision binding.
- **scope:** runtime models and tests.
- **dependencies:** P01-S01-T01
- **acceptance criteria:** state cannot reference a different task revision; null and terminal-state rules are explicit.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** positive and negative state fixtures pass.
- **expected outputs:** Runtime State model and identity validators.
- **completion signal:** state contract test suite passes.

#### P01-S01-T03 — Implement event, result, decision, and manifest schemas

- **objective:** Define validated records for events, worker results, HumanDecision, checkpoints, and Run Manifest.
- **scope:** contract models and fixtures; no persistence logic.
- **dependencies:** P01-S01-T02
- **acceptance criteria:** each record validates required identity, hashes, timestamps, and immutable fields; secrets are rejected from manifest/event payloads.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** schema fixtures and secret-leak regression tests pass.
- **expected outputs:** versioned record schemas and fixtures.
- **completion signal:** all record validators pass with zero known leaks.

### P01-S02 — Plan loader and validator

#### P01-S02-T01 — Load plan and pinned definitions

- **objective:** Load `.uads/plan.yaml` and its pinned definitions without using Markdown as an execution source.
- **scope:** plan loader, path resolution, schema-version handling.
- **dependencies:** P01-S01-T01
- **acceptance criteria:** missing, duplicate, revision-mismatched, objective-mismatched, and out-of-root definitions fail closed.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** loader tests cover valid and malicious paths.
- **expected outputs:** typed plan object and validation errors.
- **completion signal:** plan fixture suite passes.

#### P01-S02-T02 — Validate dependency graph and stage boundaries

- **objective:** Validate unique IDs, acyclic dependencies, stage/phase references, and eligible-task closure.
- **scope:** graph validator and tests.
- **dependencies:** P01-S02-T01
- **acceptance criteria:** cycles, missing dependencies, cross-project references, and invalid stage IDs are rejected with actionable errors.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** graph tests include cycle, fan-in, fan-out, and empty-stage cases.
- **expected outputs:** dependency graph and validation report.
- **completion signal:** graph validator passes all fixtures.

---

## P02 — Durable state and transitions

### P02-S01 — Event log and materialized state

#### P02-S01-T01 — Implement append-only event store

- **objective:** Append newline-terminated events with sequence continuity, payload hashes, flush behavior, and final-line recovery rules.
- **scope:** `.uads/events.jsonl` adapter and corruption tests.
- **dependencies:** P01-S01-T03
- **acceptance criteria:** sequence and hash violations fail closed; only a torn final non-newline line may be ignored.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** crash/corruption fixture tests pass.
- **expected outputs:** event store and integrity report.
- **completion signal:** append, replay, torn-line, and corruption tests pass.

#### P02-S01-T02 — Implement atomic state store and replay

- **objective:** Materialize `state.json`, atomically replace it, and replay events after `last_event_seq`.
- **scope:** state store, startup replay, filesystem adapter tests.
- **dependencies:** P02-S01-T01
- **acceptance criteria:** state ahead of event log is rejected; complete events without state updates are replayed; repeated replay is idempotent.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** state/event crash-consistency tests pass.
- **expected outputs:** state store and replay diagnostics.
- **completion signal:** replay suite passes twice from the same fixture.

### P02-S02 — Transition engine

#### P02-S02-T01 — Implement guarded state transitions

- **objective:** Implement the Revision 2 transition table with owner, guard, and required durable-data checks.
- **scope:** transition engine and transition tests.
- **dependencies:** P02-S01-T02, P01-S01-T02
- **acceptance criteria:** illegal transitions fail; every legal transition emits one validated event; no RUNNING-to-SUCCEEDED shortcut exists.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** transition matrix tests cover every table row and illegal adjacent state.
- **expected outputs:** transition service and transition matrix fixture.
- **completion signal:** complete transition matrix passes.

#### P02-S02-T02 — Add single-process serialization and idempotency

- **objective:** Ensure concurrent or repeated transition requests cannot duplicate attempts or event sequence numbers.
- **scope:** local lock/serialization boundary, idempotency tests and `tests/integration/` for the early bounded harness.
- **dependencies:** P02-S02-T01
- **acceptance criteria:** duplicate event IDs and stale expected-state writes are rejected; repeated startup does not create duplicate attempts.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** concurrency and retry-of-same-request tests pass. Before P03, run a temporary-repository integration harness connecting implemented task/result schemas, transitions, events and state with a bounded fake worker and deterministic test verifier. Cover success, failed verification, replay and preserved human blocks. No provider or arbitrary shell execution; this planned check does not replace P07 acceptance.
- **expected outputs:** transition idempotency implementation and evidence.
- **completion signal:** repeated transition test is deterministic across 100 iterations.

---

## P03 — Scheduling and human decisions

### P03-S01 — Eligibility and retry policy

#### P03-S01-T01 — Implement eligible-task scheduler

- **objective:** Select the highest-priority eligible task from validated plan and Runtime State.
- **scope:** scheduler, dependency checks, baseline/route hooks, scheduler tests.
- **dependencies:** P01-S02-T02, P02-S02-T01
- **acceptance criteria:** only terminal-success dependencies unlock a task; unresolved human decisions and unavailable routes block it.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** scheduler scenarios cover priority ties, blocked dependencies, and terminal stages.
- **expected outputs:** scheduler service and eligibility report.
- **completion signal:** deterministic selection fixtures pass.

#### P03-S01-T02 — Implement run/task/stage retry budgets

- **objective:** Enforce independently scoped budgets and the narrowest-exhausted-budget rule.
- **scope:** budget accounting, attempt records, retry tests.
- **dependencies:** P03-S01-T01, P02-S02-T02
- **acceptance criteria:** failed attempts are never overwritten; exhausted run/task/stage budgets produce the specified outcome.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** budget tests cover retries across one and multiple runs.
- **expected outputs:** budget evaluator and failure/budget evidence.
- **completion signal:** budget matrix passes.

### P03-S02 — Failure fingerprints and human flow

#### P03-S02-T01 — Implement failure fingerprints

- **objective:** Produce deterministic fingerprints from the specified identity, error, verifier, artifact, and route inputs.
- **scope:** fingerprint normalizer and tests.
- **dependencies:** P03-S01-T02, P01-S01-T03
- **acceptance criteria:** timestamps, attempt IDs, and log ordering do not change a fingerprint; material route/artifact changes do.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** normalization and differentiation fixtures pass.
- **expected outputs:** fingerprint function and fixtures.
- **completion signal:** stable fingerprint vectors pass.

#### P03-S02-T02 — Implement HumanDecision requests and resolution

- **objective:** Persist single-use decision requests and route approve, resolve, retry, reject, and amend-definition actions.
- **scope:** decision service, immutable decisions, transition integration, tests.
- **dependencies:** P03-S02-T01, P02-S02-T01
- **acceptance criteria:** decisions reference evidence; reuse is rejected; amendment creates a new Task Definition revision.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** decision lifecycle and revision-amendment tests pass.
- **expected outputs:** decision records and resolution service.
- **completion signal:** all decision lifecycle tests pass.

---

## P04 — Context, checkpoints, and manifests

### P04-S01 — Context Bundle

#### P04-S01-T01 — Build bounded ordered context bundles

- **objective:** Build task-relevant bundles from definition, plan, baseline, selected files, failures, and instructions.
- **scope:** context builder, path allowlist, ordering rules, tests.
- **dependencies:** P01-S01-T01, P01-S02-T01, P03-S02-T01
- **acceptance criteria:** conversation history is not implicit; out-of-scope files and secrets are excluded.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** scope, secret, ordering, and empty-source tests pass.
- **expected outputs:** Context Bundle artifact and builder API.
- **completion signal:** bundle fixtures pass policy checks.

#### P04-S01-T02 — Implement reproducible bundle identity

- **objective:** Hash canonical bundle metadata and content references exactly as specified.
- **scope:** canonical JSON/hash implementation and reproducibility tests.
- **dependencies:** P04-S01-T01
- **acceptance criteria:** same inputs reproduce the same identity; any source, order, builder-version, or content change changes it.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** hash vectors and mutation tests pass.
- **expected outputs:** bundle hash and identity verifier.
- **completion signal:** reproducibility suite passes.

### P04-S02 — Repository baseline and run binding

#### P04-S02-T01 — Implement checkpoint capture and baseline policies

- **objective:** Capture HEAD, dirty state, diff, untracked paths, and enforce allow-and-preserve, require-clean, and allow-listed policies.
- **scope:** repository adapter, checkpoint artifacts, policy tests.
- **dependencies:** P02-S01-T02
- **acceptance criteria:** user changes are never silently reset or attributed; policy is checked before routing.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** clean, dirty, untracked, and allow-list scenarios pass.
- **expected outputs:** checkpoint artifact set and baseline decision.
- **completion signal:** baseline policy matrix passes.

#### P04-S02-T02 — Implement immutable Run Manifest

- **objective:** Bind plan, definition, route, context, checkpoint, configuration, and budgets before execution.
- **scope:** manifest creation/validation and tests.
- **dependencies:** P04-S01-T02, P04-S02-T01, P01-S01-T03
- **acceptance criteria:** manifest is immutable; hashes and identities match referenced artifacts; secrets are by name only.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** manifest tamper and cross-reference tests pass.
- **expected outputs:** run-manifest adapter and verification report.
- **completion signal:** manifest integrity suite passes.

---

## P05 — Routing and execution supervision

### P05-S01 — Profiles, bindings, and route resolution

#### P05-S01-T01 — Implement logical profiles and physical bindings

- **objective:** Validate capability profiles and provider model bindings without coupling Task Definitions to vendors.
- **scope:** profile/binding schemas, configuration loading, capability tests.
- **dependencies:** P01-S01-T03
- **acceptance criteria:** bindings cannot claim absent capabilities; pinned provider/model/api fields are retained.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** compatibility and invalid-capability fixtures pass.
- **expected outputs:** profile and binding registry.
- **completion signal:** binding validation suite passes.

#### P05-S01-T02 — Implement deterministic Route Resolver

- **objective:** Select and validate the complete profile/binding/executor/provider/parser tuple.
- **scope:** route resolver, fallback precedence, compatibility checks, tests.
- **dependencies:** P05-S01-T01, P04-S01-T02
- **acceptance criteria:** explicit-task, project, profile-default, and fallback order is deterministic; incompatible routes become `NEEDS_HUMAN`.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** route compatibility and fallback tests pass.
- **expected outputs:** route decision and incompatibility reasons.
- **completion signal:** route matrix passes.

### P05-S02 — Supervisor lifecycle

#### P05-S02-T01 — Implement local executor protocol

- **objective:** Define the minimal executor adapter that accepts a Context Bundle and returns raw structured-result artifacts.
- **scope:** executor interface and local fake executor; no external provider SDK.
- **dependencies:** P04-S02-T02, P05-S01-T02
- **acceptance criteria:** executor cannot directly mark success; raw output is persisted before parsing.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** success, failure, malformed-output, and crash fake-executor tests pass.
- **expected outputs:** executor adapter and test doubles.
- **completion signal:** executor protocol suite passes.

#### P05-S02-T02 — Implement leases, heartbeats, and timeouts

- **objective:** Manage startup, idle, maximum, shutdown-grace, attempt leases, and interruption evidence.
- **scope:** Execution Supervisor and lifecycle tests.
- **dependencies:** P05-S02-T01, P02-S02-T02
- **acceptance criteria:** monotonic time is used; stale work becomes `INTERRUPTED`; duplicate leases are rejected.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** fake-clock timeout and restart tests pass.
- **expected outputs:** supervisor lifecycle service and timeout evidence.
- **completion signal:** lifecycle matrix passes.

---

## P06 — Results and verification

### P06-S01 — Result Parser

#### P06-S01-T01 — Validate and persist worker results

- **objective:** Parse `task_result_v1`, validate identity, status, changed paths, artifacts, and evidence.
- **scope:** parser, raw-result storage, schema tests.
- **dependencies:** P05-S02-T01, P01-S01-T03
- **acceptance criteria:** malformed, missing, contradictory, or identity-mismatched output becomes `INVALID_WORKER_RESULT` and `NEEDS_HUMAN`.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** result fixture matrix passes; raw output is retained.
- **expected outputs:** parsed result and parser diagnostics.
- **completion signal:** valid/invalid result suite passes.

### P06-S02 — Verification

#### P06-S02-T01 — Implement deterministic acceptance checks

- **objective:** Run and record schema, path, formatting, type, test, hash, dependency, and policy checks selected by acceptance criteria.
- **scope:** verifier registry, command capture, evidence records.
- **dependencies:** P06-S01-T01, P01-S01-T01
- **acceptance criteria:** commands, inputs, exit codes, and artifacts are reproducible; safety checks cannot be overridden by semantic review.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** verifier tests cover pass, fail, missing-command, and out-of-scope changes.
- **expected outputs:** deterministic verification report.
- **completion signal:** verifier matrix passes.

#### P06-S02-T02 — Implement semantic verification and independent review

- **objective:** Support declared evaluator/profile, cited artifacts, uncertainty, reviewer independence, and disagreement escalation.
- **scope:** semantic review adapter, reviewer policy, tests using deterministic fake evaluators.
- **dependencies:** P06-S02-T01, P05-S01-T01
- **acceptance criteria:** executor's success assertion is not authority; disagreement becomes `NEEDS_HUMAN`.
- **recommended executor/model profile:** independent reviewer / `coding-reasoning`
- **quality gate:** independent-review and deterministic-failure precedence tests pass.
- **expected outputs:** semantic report and reviewer decision.
- **completion signal:** review policy suite passes.

---

## P07 — Recovery, security, and end-to-end flow

### P07-S01 — Startup reconciliation and recovery

#### P07-S01-T01 — Reconcile interrupted attempts

- **objective:** Recover `RUNNING`, `ROUTED`, `PARSING`, and `VERIFYING` attempts using manifests, checkpoints, leases, and committed raw results.
- **scope:** startup reconciliation and recovery tests.
- **dependencies:** P05-S02-T02, P06-S01-T01, P02-S01-T02
- **acceptance criteria:** committed results resume parsing/verification; missing results recover or retry with a new attempt ID; exhausted budgets reach `NEEDS_HUMAN`.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** crash-point matrix passes and startup is idempotent.
- **expected outputs:** reconciliation report and recovery events.
- **completion signal:** recovery matrix passes twice from identical state.

### P07-S02 — Security and audit

#### P07-S02-T01 — Enforce path, command, and secret boundaries

- **objective:** Apply trust-boundary rules to worker output, repository content, external responses, paths, commands, and secrets.
- **scope:** policy enforcement and adversarial tests.
- **dependencies:** P04-S01-T01, P04-S02-T01, P05-S02-T01
- **acceptance criteria:** prose cannot trigger commands; out-of-scope access and secret exposure fail closed; evidence remains auditable.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** adversarial fixture suite passes.
- **expected outputs:** security policy module and audit evidence.
- **completion signal:** boundary tests pass with zero known bypasses.

#### P07-S02-T02 — Run the complete local reference flow

- **objective:** Demonstrate plan validation through scheduling, routing, execution, parsing, verification, persistence, and next-task selection.
- **scope:** end-to-end fixtures and one documented local run.
- **dependencies:** P07-S01-T01, P07-S02-T01, P06-S02-T02, P03-S02-T02
- **acceptance criteria:** successful, retryable-failure, invalid-result, human-decision, and interrupted-run paths are demonstrated.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** end-to-end suite passes from a fresh temporary repository.
- **expected outputs:** run artifacts, reports, and reference-flow documentation.
- **completion signal:** all five paths complete with valid event/state consistency.

---

## P08 — Hardening and V1 release gate

### P08-S01 — Compatibility and operational hardening

#### P08-S01-T01 — Test configuration precedence and provenance

- **objective:** Implement and verify defaults through runtime overrides, including non-weakenable safety rules.
- **scope:** configuration resolver, provenance records, tests.
- **dependencies:** P05-S01-T02, P04-S02-T02
- **acceptance criteria:** source for every overridden key is recorded; safety, identity, and audit requirements cannot be weakened.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** precedence and forbidden-override matrix passes.
- **expected outputs:** resolved configuration and provenance report.
- **completion signal:** configuration suite passes.

#### P08-S01-T02 — Verify repeatability and failure diagnostics

- **objective:** Exercise repeated runs, corrupted artifacts, partial writes, and representative large plans within documented limits.
- **scope:** hardening tests and diagnostics; no speculative performance subsystem.
- **dependencies:** P07-S02-T02, P08-S01-T01
- **acceptance criteria:** failures produce actionable fingerprints and no silent recovery; documented limits are measured.
- **recommended executor/model profile:** local-process executor / `coding-reasoning`
- **quality gate:** repeatability, corruption, and diagnostic tests pass.
- **expected outputs:** hardening report and known-limit ledger.
- **completion signal:** hardening checklist is green or explicitly escalated.

### P08-S02 — Release baseline

#### P08-S02-T01 — Complete implementation acceptance checklist

- **objective:** Map every Revision 2 minimum acceptance criterion to code, test, and evidence.
- **scope:** traceability matrix and missing-evidence fixes only.
- **dependencies:** P08-S01-T02
- **acceptance criteria:** all 15 criteria have direct evidence; unresolved items are `NEEDS_HUMAN`, not marked complete.
- **recommended executor/model profile:** independent reviewer / `coding-reasoning`
- **quality gate:** independent review of the traceability matrix.
- **expected outputs:** V1 traceability matrix and review report.
- **completion signal:** 15/15 criteria evidenced and reviewer signs off.

#### P08-S02-T02 — Freeze V1 technical baseline

- **objective:** Freeze schemas, transition semantics, artifact formats, and the reference-flow evidence as the V1 baseline.
- **scope:** version metadata, release documentation, final checks; no new features.
- **dependencies:** P08-S02-T01
- **acceptance criteria:** full test suite passes; plan and Task Definition hashes are recorded; known limitations and deferred work are listed.
- **recommended executor/model profile:** independent reviewer / `coding-reasoning`
- **quality gate:** clean release run from a fresh checkout or equivalent clean workspace.
- **expected outputs:** V1 baseline report, hashes, and release notes.
- **completion signal:** `V1_BASELINE_FROZEN` event plus archived evidence bundle.

---

## Stop conditions and deferred scope

The implementation stops at the first failed Stage quality gate. Provider-specific production integrations, distributed queues, UI, multi-process locking, and performance optimization are deferred until the local reference flow is green and a measured requirement justifies them.
