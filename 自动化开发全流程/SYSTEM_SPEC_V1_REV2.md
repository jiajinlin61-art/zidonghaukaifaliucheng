# Universal AI Development System V1
## System Specification — Revision 2

**Status:** Architecture baseline for implementation  
**Revision:** 1.0 Rev 2  
**Scope:** General-purpose AI-assisted software development orchestration

---

## 1. Purpose and non-goals

The system coordinates planned software-development work from a machine-readable plan through execution, verification, durable state, and the next eligible task.

The system preserves these boundaries:

```text
Model              ≠ Executor
Execution          ≠ Verification
State              ≠ History
Context            ≠ Conversation
Framework          ≠ HR Pilot
Logical Model      ≠ Physical Binding
Task Definition   ≠ Runtime State
```

The primary control flow remains:

```text
Plan
  ↓
Task Contract
  ↓
Orchestrator
  ↓
Route Resolver
  ↓
Execution Supervisor
  ↓
Executor
  ↓
Result Parser
  ↓
Verification
  ↓
State / Checkpoint
  ↓
Next Task
```

This revision specifies contracts and failure boundaries. It does not prescribe a vendor, model provider, UI, distributed queue, or database.

---

## 2. Repository layout and sources of truth

Human-readable documents remain useful for review, but orchestration decisions must use structured files.

```text
project/
├── SYSTEM_SPEC_V1_REV2.md
├── IMPLEMENTATION_PLAN.md
├── docs/
│   └── DEVELOPMENT.md
├── .uads/
│   ├── plan.yaml
│   ├── config.yaml                 # optional project configuration
│   ├── state.json                  # current materialized state
│   ├── events.jsonl                # append-only event log
│   ├── run-manifest.json           # one file per run or current run pointer
│   ├── checkpoints/
│   ├── contexts/
│   └── tasks/
│       └── <task-id>.yaml              # immutable Task Definition
```

`IMPLEMENTATION_PLAN.md` is the human-readable explanation. `.uads/plan.yaml` is the scheduler's source of truth. A mismatch is a plan validation error, not a reason to guess.

### 2.1 Machine-readable plan

```yaml
schema_version: "1.0"
project_id: "uads-v1"
default_branch: "main"

phases:
  - id: P01
    title: Core Contracts and State
    stages:
      - id: P01-S01
        title: Core Contracts
        tasks:
          - id: P01-S01-T01
            title: Implement TaskContract
            objective: Define and validate the task contract schema.
            revision: 1
            definition: .uads/tasks/P01-S01-T01.yaml
            dependencies: []
            priority: 100
            retry_budget:
              task: 2
              stage: 4
              run: 1
```

Required identifiers are unique within the plan. Dependencies must refer to existing tasks, form an acyclic graph, and be satisfied before scheduling. The plan validator also checks that each definition file exists and that its declared `task_id`, `revision`, and objective match the plan entry.

---

## 3. Task Contract

The Task Contract has two separate records.

### 3.1 Task Definition

The Task Definition is the immutable, reviewable intent of work. It is versioned and content-addressed.

```yaml
schema_version: "1.0"
task_id: P01-S01-T01
revision: 1
title: Implement TaskContract
objective: Define and validate the task contract schema.
scope:
  include:
    - src/uads/contracts/task.py
    - tests/contracts/
  exclude:
    - deployment
inputs: [SYSTEM_SPEC_V1_REV2.md, IMPLEMENTATION_PLAN.md]
dependencies: []
acceptance_criteria:
  - id: AC-01
    statement: Contract rejects missing task_id.
    verification: automated
risk: medium
complexity: low
allowed_changes:
  paths: [src/uads/contracts/task.py, tests/contracts/]
retry_budget:
  task: 2
  stage: 4
  run: 1
```

Paths in `scope.include`, `scope.exclude`, and top-level `allowed_changes.paths` are repository-relative; directories include descendants and exclusions win. In the bootstrap seed, `allowed_changes.paths` equals `scope.include`. The optional `scope_description` and `non_goals` retain human constraints. Unpublished seed correction is documented in `docs/DEVELOPMENT.md`; it is not a completed runtime task.

A worker cannot mutate the definition. If the objective, scope, acceptance criteria, dependencies, or routing requirements change, create a new revision and schedule that revision explicitly.

### 3.2 Runtime State

Runtime State records what happened while executing one definition revision. It is mutable only through validated state transitions.

```yaml
task_id: P01-S01-T01
revision: 1
run_id: run-2026-001
state: READY
attempt: 0
selected_route: null
context_bundle_hash: null
failure_fingerprint: null
last_event_seq: 0
checkpoint_id: null
result_id: null
human_decision_id: null
```

A runtime state must never silently point to a different task revision. A resumed run either uses the same `task_id + revision` or starts a new run with an explicit revision.

### 3.3 Revision rules

`revision` is a positive integer scoped to `task_id`. A revision is immutable after it is published. Its canonical hash covers normalized definition bytes, schema version, and referenced acceptance criteria. A plan entry must pin the revision. Runtime events include both task ID and revision so old events cannot be applied to a newer definition.

---

## 4. Orchestrator and scheduling

The Orchestrator loads `.uads/plan.yaml`, validates the graph, loads the pinned Task Definition, reads Runtime State, and selects the highest-priority eligible task. Eligibility requires:

1. all dependencies are terminal-success;
2. no unresolved human decision blocks the task;
3. the retry budget is available;
4. the repository baseline policy permits execution;
5. a compatible route exists.

The Orchestrator owns scheduling and state transitions. It does not execute model output and does not decide whether arbitrary worker prose is a successful result.

### 4.1 Retry budgets

Budgets are independently enforced at three scopes. A budget value counts additional retries after the initial attempt; it does not count the initial attempt itself. For example, `task: 2` permits at most three task attempts: one initial attempt plus two retries.

| Scope | Counts | Exhaustion result |
|---|---|---|
| Run | retries of one `run_id` after its initial attempt | `NEEDS_HUMAN` |
| Task | retries of one task revision across runs | `NEEDS_HUMAN` |
| Stage | retried attempts across tasks in one stage | stage blocked and `NEEDS_HUMAN` |

The narrowest exhausted budget wins. Budget exhaustion is not equivalent to a deterministic task failure: it requires an explicit human decision to amend the definition, route, or budget, or to stop the task. A retry is allowed only after a new attempt ID is recorded; it must not overwrite the failed attempt.

---

## 5. State machine

### 5.1 States

```text
PLANNED → READY → ROUTED → RUNNING → PARSING → VERIFYING → SUCCEEDED
VERIFYING → READY                 (retryable failure, budget available)
VERIFYING → FAILED or NEEDS_HUMAN
RUNNING → INTERRUPTED → READY     (reconciled, no human block, budget available)
INTERRUPTED → PARSING or VERIFYING (committed result, no human block)
NEEDS_HUMAN → RESOLVED → READY, SUCCEEDED or FAILED
```

The transition table below is authoritative; this diagram only summarizes the main paths.

`INTERRUPTED` means the process stopped before a terminal outcome was durably recorded. It is not equivalent to `FAILED` and is recoverable after startup reconciliation. A shutdown never clears a pending human decision or other blocking reason: reconciliation restores `NEEDS_HUMAN` when such a block exists; otherwise it may restore `READY` only after durable recovery evidence.

`RETRYABLE` is a decision outcome, not a persisted runtime state. It is emitted by verification when a retryable failure has remaining budget; the Orchestrator records the fingerprint and performs the explicit `VERIFYING → READY` transition. No event may target `RETRYABLE` as a state.

### 5.2 Complete State Transition Table

| Current | Event / guard | Next | Owner | Required durable data |
|---|---|---|---|---|
| PLANNED | plan validated and dependencies satisfied | READY | Orchestrator | plan revision |
| READY | compatible route selected | ROUTED | Orchestrator | route ID, model/executor/provider |
| READY | no route or invalid definition | NEEDS_HUMAN | Orchestrator | reason, fingerprint |
| ROUTED | supervisor starts attempt | RUNNING | Supervisor | attempt ID, start time, manifest |
| ROUTED | startup cannot begin | FAILED | Supervisor | error, fingerprint |
| RUNNING | heartbeat received | RUNNING | Supervisor | heartbeat timestamp |
| RUNNING | worker returns a bounded result | PARSING | Supervisor | raw result artifact, end time |
| RUNNING | process crash, lease loss, or restart before result commit | INTERRUPTED | Supervisor | interruption reason |
| RUNNING | max execution timeout | INTERRUPTED | Supervisor | timeout kind, termination evidence |
| PARSING | result schema valid | VERIFYING | Result Parser | parsed result, parser version |
| PARSING | malformed, missing, or contradictory result | NEEDS_HUMAN | Result Parser | `INVALID_WORKER_RESULT`, raw artifact |
| VERIFYING | all required checks pass | SUCCEEDED | Verifier | verification report |
| VERIFYING | retryable check or execution failure and budget remains | READY | Orchestrator | failure fingerprint, retry number |
| VERIFYING | non-retryable deterministic failure | FAILED | Orchestrator | failure fingerprint, report |
| VERIFYING | retryable failure but applicable retry budget exhausted | NEEDS_HUMAN | Orchestrator | failure fingerprint, budget report |
| VERIFYING | ambiguous, unsafe, or policy-sensitive outcome | NEEDS_HUMAN | Verifier | decision request |
| INTERRUPTED | no committed result, no human/policy block, and budget available | READY | Orchestrator | recovery event, new attempt ID |
| INTERRUPTED | committed result exists and no unresolved human/policy block | PARSING or VERIFYING | Orchestrator | recovered artifact reference |
| INTERRUPTED | unresolved human/policy block, or no committed result and retry budget exhausted | NEEDS_HUMAN | Orchestrator | blocking request or budget report |
| NEEDS_HUMAN | valid approval/resolve decision | RESOLVED | Human / Orchestrator | `HumanDecision` |
| NEEDS_HUMAN | reject decision | FAILED | Human / Orchestrator | `HumanDecision`, reason |
| NEEDS_HUMAN | request retry decision | READY | Human / Orchestrator | `HumanDecision`, new attempt policy |
| RESOLVED | resolution permits execution | READY | Orchestrator | resolution reference |
| RESOLVED | resolution declares success | SUCCEEDED | Orchestrator | decision plus evidence |
| RESOLVED | resolution declares failure | FAILED | Orchestrator | decision plus reason |
| ROUTED / RUNNING / PARSING / VERIFYING without a human/policy block | shutdown signal or stale attempt on restart | INTERRUPTED | Supervisor | prior state, shutdown/restart reason, artifact references, last heartbeat |
| PLANNED / READY / RESOLVED | shutdown signal | unchanged | Supervisor | existing guards, decision references and shutdown reason |
| any non-terminal with an unresolved human/policy block | shutdown signal | NEEDS_HUMAN | Supervisor | shutdown reason, blocking request, last heartbeat |
| SUCCEEDED / FAILED | any new work requested | PLANNED | Orchestrator | new task revision or run |
```

No component may jump directly from `RUNNING` to `SUCCEEDED` without a parsed result and required verification evidence.

---

## 6. Execution Supervisor

The Execution Supervisor owns process lifecycle, leases, heartbeats, output capture, and timeouts. It is separate from the executor and from the Orchestrator.

### 6.1 Startup protocol

At startup the Supervisor:

1. loads `state.json` and replays complete `events.jsonl` records with `seq > last_event_seq`;
2. identifies `RUNNING`, `ROUTED`, `PARSING`, or `VERIFYING` attempts without a terminal commit;
3. checks the run manifest and checkpoint references;
4. preserves unresolved human/policy requests as `NEEDS_HUMAN`; only unblocked stale attempts become `INTERRUPTED` with their prior state and artifact references;
5. asks the Orchestrator whether to resume parsing, recover, retry, or request human action;
6. acquires a single attempt lease before starting a worker.

Startup must be idempotent. Repeating it cannot create a second attempt for the same attempt ID.

### 6.2 Idle and maximum timeouts

Each route defines:

- `startup_timeout`: maximum time before a worker is considered started;
- `idle_timeout`: maximum interval without a heartbeat or accepted output;
- `max_execution_timeout`: hard wall-clock limit for the attempt;
- `shutdown_grace_period`: time allowed for clean termination.

On idle timeout, the Supervisor first requests a heartbeat, then terminates after the grace period if no valid heartbeat arrives. On maximum timeout it terminates unconditionally, records evidence, and transitions to `INTERRUPTED`; policy then decides retry versus human review. Timeouts are measured by the Supervisor's monotonic clock, not worker-reported timestamps.

---

## 7. Logical Model Profile and Physical Model Binding

A Logical Model Profile describes required capabilities without naming a concrete model:

```yaml
profile_id: coding-reasoning
capabilities: [code_editing, tool_use, structured_output]
context_window_min: 32000
output_format: task_result_v1
quality_tier: medium
```

A Physical Model Binding maps the profile to an actual provider model:

```yaml
binding_id: openai-coding-1
provider: openai
model: <provider-model-id>
profile_id: coding-reasoning
api_version: <pinned-version>
```

The profile is stable system policy. The binding is deployment configuration and may change without changing a Task Definition. A binding must not claim capabilities absent from the physical model.

---

## 8. Route Resolver

The Route Resolver selects a complete compatible tuple:

```text
Logical Model Profile
  + Physical Model Binding
  + Executor
  + Provider adapter
  + Result schema/parser
```

Compatibility is checked before execution for:

- logical profile capabilities versus binding capabilities;
- model versus executor protocol;
- executor versus provider authentication and tool support;
- output format versus Result Parser version;
- context-window requirement versus Context Bundle size;
- repository permissions versus requested scope;
- timeout and retry policy availability.

If no tuple passes validation, the task enters `NEEDS_HUMAN` with a route incompatibility reason. Fallback selection is deterministic: explicit task route, project route, profile default, then configured fallback. A fallback must still pass all compatibility checks.

---

## 9. Context Bundle

The Context Builder creates a bounded, ordered bundle containing only task-relevant material: Task Definition, applicable plan nodes, repository baseline, selected files, prior failure evidence, and required instructions.

```json
{
  "bundle_id": "ctx-...",
  "task_id": "P01-S01-T01",
  "task_revision": 1,
  "source_refs": [{"path":"src/contracts/task.py","sha256":"..."}],
  "ordered_sections": ["contract", "plan", "baseline", "files", "failures"],
  "builder_version": "1",
  "sha256": "..."
}
```

`Context Bundle identity` is the hash of canonical JSON over task ID/revision, source references, section order, builder version, and content hashes. The same identity must reproduce the same bundle, or the bundle is invalid. Conversation history is not an implicit source.

---

## 10. Worker result and Result Parser

Workers return a structured result, not a success claim in prose.

```json
{
  "schema": "task_result_v1",
  "status": "completed",
  "summary": "...",
  "changed_paths": ["..."],
  "evidence": [{"kind":"test", "command":"...", "result":"passed"}],
  "artifacts": ["..."],
  "failure": null
}
```

The Result Parser validates schema, allowed status values, task/run identity, changed paths, referenced artifacts, and required evidence. It stores the raw result before parsing. Missing, malformed, identity-mismatched, or internally contradictory output produces the terminal parsing error `INVALID_WORKER_RESULT`; it must not be treated as an ordinary task failure. The parser transitions to `NEEDS_HUMAN` because the system cannot safely infer intent.

---

## 11. Verification

Verification is independent of execution and is selected from acceptance criteria.

### 11.1 Deterministic verification

Deterministic checks include schema validation, file existence, formatting, type checks, tests, exit codes, hashes, dependency closure, and policy checks. Their inputs and commands must be recorded so they can be reproduced.

### 11.2 Semantic verification

Semantic checks assess behavior or intent that cannot be reduced to a stable command, such as whether an implementation satisfies a narrative acceptance criterion. Semantic verification must cite the examined artifacts, use a declared evaluator/profile, and report uncertainty. It cannot override a failed deterministic safety check.

### 11.3 Independent Reviewer principle

The executor must not be the sole reviewer of its own work. Where review is required, the reviewer receives the Task Definition, Context Bundle identity, changed artifacts, and verification evidence, but not an untrusted success assertion as authority. The reviewer must be independent by process, model binding, or human decision. Reviewer disagreement produces `NEEDS_HUMAN`.

---

## 12. Checkpoints and repository baseline

Before each attempt, the system records a Checkpoint:

```json
{
  "checkpoint_id": "cp-...",
  "repository": "...",
  "git_head": "<commit-sha-or-null>",
  "branch": "main",
  "dirty_state": true,
  "status_digest": "...",
  "diff_artifact": ".uads/checkpoints/cp-.../diff.patch",
  "untracked_artifact": ".uads/checkpoints/cp-.../untracked.txt",
  "created_at": "..."
}
```

`git_head` is the exact HEAD at checkpoint creation. `dirty_state` records whether tracked or untracked changes existed. The full diff and untracked-path listing are stored as artifacts when permitted. A dirty baseline is not silently discarded, reset, or attributed to the worker.

Project configuration selects one of these baseline policies:

- `allow-and-preserve`: run against existing changes and distinguish new changes;
- `require-clean`: refuse execution when dirty;
- `allow-listed`: permit only configured paths.

The policy is checked before routing and recorded in the run manifest.

---

## 13. Failure fingerprints

A failure fingerprint groups materially identical failures without conflating unrelated ones. Its canonical inputs are:

```text
task_id + task_revision + phase/stage + error_code
+ normalized exception type/message
+ failing command or verifier ID
+ stable failing path/interface identity
```

The fingerprint excludes timestamps, attempt IDs, model/executor/session identity, artifact hashes, and nondeterministic log ordering. Those values belong to the attempt context and remain available for reproduction and audit. It is used for retry budgets, deduplication, and escalation, so changing model, executor, or session cannot reset the same failure count. A materially different error code, normalized root cause, failing command/verifier, or stable failing path/interface may create a new fingerprint.

---

## 14. Human intervention

`NEEDS_HUMAN` is a durable state, not an informal pause. The system creates a decision request containing task/revision, run, reason code, evidence, proposed options, and expiry.

The human flow is:

```text
NEEDS_HUMAN
   ↓
decision request
   ↓
resolve / approve / reject
   ↓
RESOLVED
   ↓
READY, SUCCEEDED, or FAILED
```

```json
{
  "human_decision_id": "hd-...",
  "request_id": "req-...",
  "actor_id": "user-or-system",
  "action": "approve | resolve | reject",
  "reason": "...",
  "selected_option": "retry | accept | change-route | amend-definition",
  "scope": "this-attempt | this-task | this-stage",
  "created_at": "..."
}
```

`approve` permits the proposed action; `resolve` supplies an explicit resolution or corrected evidence; `reject` terminates the blocked work. A decision is immutable, single-use for its request, and must reference the evidence considered. Amending a Task Definition always creates a new revision.

---

## 15. Durable events and crash consistency

`events.jsonl` is the append-only history. `state.json` is the materialized current state. Every event has a monotonically increasing `seq`, unique `event_id`, task/revision/run identity, timestamp, previous state, next state, and payload hash.

The commit protocol is:

1. validate the transition and construct the event;
2. append the event as one newline-terminated record and flush it;
3. atomically replace `state.json` with a file whose `last_event_seq` equals the appended event's `seq`;
4. flush the replacement and its directory where supported;
5. only then acknowledge the transition.

On startup, the system reads `last_event_seq`, verifies event continuity and payload hashes, and replays events after that sequence. A complete event with no state update is replayed. A torn final JSON line is ignored only if it is the final physical line and has no valid newline; any earlier corruption is an integrity error requiring human intervention. A state file ahead of the event log is also an integrity error. No event is deleted to repair divergence.

---

## 16. Configuration precedence

Configuration is resolved in this order, from lowest to highest precedence:

```text
system defaults
  < provider defaults
  < user configuration
  < repository .uads/config.yaml
  < project/phase/stage configuration
  < task definition explicit fields
  < run-time operator override
```

Higher precedence may narrow permissions and budgets but may not weaken mandatory safety rules, identity checks, or audit requirements. The resolved configuration and its source for each overridden key are recorded in the run manifest. Secrets are referenced by name, never copied into manifests or events.

---

## 17. Run Manifest

Each run has an immutable manifest created before execution:

```json
{
  "run_id": "run-2026-001",
  "project_id": "uads-v1",
  "task_id": "P01-S01-T01",
  "task_revision": 1,
  "plan_hash": "...",
  "task_definition_hash": "...",
  "route": {
    "profile_id": "coding-reasoning",
    "binding_id": "openai-coding-1",
    "executor_id": "..."
  },
  "context_bundle_hash": "...",
  "checkpoint_id": "cp-...",
  "repository_baseline": {"git_head":"...", "dirty_state":true},
  "resolved_config_hash": "...",
  "retry_budgets": {"run":1,"task":2,"stage":4},
  "supervisor": {"startup_timeout":60,"idle_timeout":300,"max_execution_timeout":3600},
  "created_at": "..."
}
```

The manifest binds the exact plan, definition, route, context, repository baseline, configuration, and budgets used by a run. It is required evidence for resume, review, and post-run diagnosis.

---

## 18. Security, integrity, and audit requirements

- Treat worker output, repository content, logs, and external tool responses as untrusted data.
- Enforce path scope before reading or writing files.
- Never execute a command solely because a worker placed it in prose.
- Record identity, authorization, route, and artifact hashes for every material transition.
- Preserve raw worker output and verifier evidence under controlled artifact paths.
- Do not expose provider secrets in context bundles, events, checkpoints, or manifests.
- Fail closed when identity, event continuity, result schema, or repository baseline cannot be verified.

---

## 19. Minimum implementation acceptance criteria

An implementation conforms to this revision when it can demonstrate:

1. plan validation from `.uads/plan.yaml` without parsing Markdown;
2. immutable Task Definition plus separate Runtime State;
3. revision-pinned scheduling and event identity;
4. every state transition in the table, including `INTERRUPTED`;
5. startup reconciliation and supervisor timeout behavior;
6. logical profile to physical binding and route compatibility checks;
7. checkpoint evidence containing git HEAD, dirty state, and diff artifact;
8. reproducible Context Bundle identity/hash;
9. deterministic failure fingerprints and task/stage/run budgets;
10. `INVALID_WORKER_RESULT` handling;
11. deterministic and semantic verification with independent review;
12. human resolve/approve/reject flow with immutable `HumanDecision`;
13. crash-consistent `events.jsonl` / `state.json` updates with `last_event_seq`;
14. configuration precedence and provenance;
15. repository baseline policy and immutable run manifest.

This revision extends the original architecture; it does not replace its Plan → Contract → Orchestrator → Routing → Executor → Verification → State → Next Task lifecycle.
