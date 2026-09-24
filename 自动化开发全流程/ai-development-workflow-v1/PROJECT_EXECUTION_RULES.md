# Project Execution Rules

- 先读规则、需求/Brief、PROJECT_START_GATE、状态、契约和相关代码，再改动。
- 新项目命中 FULL、COMPLEX/CRITICAL、HIGH/CRITICAL risk、跨系统、架构变更或用户明确要求先确认计划时，必须先完成并展示开发计划；Project Start / Plan Approval Gate 未明确 APPROVED 前，禁止进入业务代码 Implementation。
- FULL 或确有多组依赖/跨模块集成/长期 Gate 的项目使用 Phase → Stage → Task；普通 STANDARD 不强制制造 Phase/Stage。不得整包吞实现。
- 只修改 Task 范围，保留已有改动。
- 信任边界必须验证，失败必须可见且不可静默吞掉。
- 每个实现 Task 必须有 Execution Request 1.3；在 Worker 启动前真实运行 model_router 和 route_preflight，并把 resolved_execution / resolved_review、命令、exit code 和 evidence 写入 Request。
- Controller 默认不兼任 routed Worker。只有 Request 显式授权 controller_worker_override 并记录原因时才允许直接实现；不得借此降低最低能力要求。
- Worker 必须实际使用 resolved_execution 指定的 profile/backend/model/effort，并记录独立 session、真实 invocation、diff/changed paths 和验证证据。声明“使用某模型”但没有真实 invocation evidence 视为 Gate FAIL。
- 每个 Task 必须有可重复验证和独立 Review；Reviewer 必须独立 Session，模型 Reviewer 必须与 resolved_review 一致并记录 invocation evidence。作者自审不算独立 Review。
- 只有实际存在的 Stage/Phase 才要求对应 Gate；不得为普通 STANDARD 人为制造空 Gate。
- Model 与 Executor 解耦；项目级 Task 不写死 provider/model id，但 Execution Request 的 resolved route 必须具体且可验证。
- Profile Override 必须记录原因，且不能降低 Complexity/Risk 要求的最低能力。
- 执行层只维护 task revision、attempt、route、失败计数和证据；delegated_worker 不更新项目级 NEXT/DONE。
- 上下文不足先 checkpoint，不猜测历史；checkpoint 不是第二套项目计划。
- 已有授权范围内按 Gate 连续推进；尚未授权的破坏性、外部、付费、权限或凭据变更和业务取舍需人工批准，明确人工检查点必须遵守。
- 完成前检查 diff、测试结果、dirty state、request/result identity、route identity、review independence 和未验证事项。

## Additional execution checklist

- Before functional implementation, present a task-sized plan for every new feature request or material scope change, set explicit_plan_approval_required=true, and wait for explicit approval. Continue approved work without repeated permission requests; obtain renewed approval only for scope changes or existing human checkpoints.
- Keep the approved user goal and non-goals visible in each Task Contract. Recheck them at Task start and Stage/Phase integration. If the next implementation step redirects the intended product outcome, stop and resolve the plan before coding further.
- Run the nearest relevant check for each coherent Task/change set. After fixing a failure, rerun that check and affected regressions; use full-suite and end-to-end checks at integration/release Gates, not after every small edit.
- At intake, use skills when the user requests them or they directly help the task; record invoked skills and their purpose. Use Ponytail only when the user explicitly requests it.
- At Stage/Phase Gates, record concise lessons linked to existing evidence. For a standalone FAST task, add a result note only when there is a reusable failure or improvement; do not create a separate retrospective by default.
- Handoffs carry goal/scope, Task Contract, allowed paths, architecture decisions, workspace state, verification requirements, retry/failure history, and next action. The receiver checks the live workspace before proceeding.
- If both frontend and backend are present, place them in `frontend/` and `backend/` respectively, define the API contract, and include separate startup/build checks in the plan.
