# Universal AI Development Workflow V1

## 运行形态

本工作流支持两种形态：

1. standalone_master：Codex/其他主控直接管理整个项目。
2. delegated_worker：上层 Project Controller（例如 GPT-TaskBoard）只交付一个 Task Contract，本工作流负责选择角色、模型、实现、Debug、Review 和返回证据。

两种形态共享同一套 Task Contract、Quality Gate、Retry/Escalation 和 Model Routing；delegated_worker 不自行领取下一个项目级 Task。

## 生命周期

Project Intake → Complexity Assessment → Mode Selection → Scope/Spec → Project Start / Plan Approval Gate → Task Contract → Route → Route Preflight → Implementation → Verification → Independent Review → Integration。复杂项目再按需要展开 Phase / Stage / Release Review / Retrospective。

不是每个项目都需要全部文档；模式决定最小文档集合。日常只读取入口规则、当前需求/状态、任务契约与相关代码，遇到对应决策时再读取策略和模板；历史结果只按当前问题检索。新项目命中 FULL、COMPLEX/CRITICAL、HIGH/CRITICAL risk、跨系统、架构变更或显式“先确认计划”要求时，Project Start Gate 为硬门禁：在需求、架构、开发计划尚未准备完毕或用户尚未明确确认前，Implementation 必须 BLOCKED。delegated_worker 从“Task Contract → Route”开始，但必须收到 APPROVED/NOT_REQUIRED 的 Gate 引用。

## 角色

- Project Controller：项目目标、Roadmap、任务依赖、READY/BLOCKED/DONE。可由外部 GPT-TaskBoard 或 standalone master 承担。
- Planner：架构、复杂方案和执行拆解。
- Worker：受限范围实现。
- Debugger：按 failure fingerprint 做根因定位和修复。
- Reviewer：独立 Session 审查 Task Contract、diff 与验证证据。

Role、Model Profile 与 Executor/Backend 相互独立。具体模型映射由 routing/MODEL_BINDINGS.yaml 决定。

## Task

每个 Task 必须有唯一 ID、目标、范围、输入、输出、验收命令、风险和停止条件。Worker 不扩大范围，不吞并未授权 Task。失败先分类、记录 fingerprint，再按策略重试或升级。

推荐使用 templates/EXECUTION_REQUEST.yaml 作为 delegated_worker 输入，使用 templates/EXECUTION_RESULT.yaml 返回结果。当前 Execution Contract 为 1.3：Request 必须携带治理 Gate、resolved execution/review route 与 preflight 证据；Result 必须携带真实 Worker/Reviewer invocation 证据。

项目级状态与执行级状态分离：

- Project Controller/TaskBoard 负责 READY/BLOCKED/REVIEW/DONE、Roadmap 和唯一 NEXT。
- Execution Request/Result 负责 task revision、attempt、route、失败计数、验证证据和独立 Review。
- checkpoint 只记录恢复所需事实，不是第二套项目计划，也不能覆盖 TaskBoard 的 NEXT。
- delegated_worker 禁止修改项目级 READY/NEXT/DONE；它只能返回 Execution Result 和状态建议。

## Model Routing

路由输入至少包括：

- purpose: planning / execute / debug / review
- complexity: TRIVIAL / SIMPLE / STANDARD / COMPLEX / CRITICAL
- risk: LOW / MEDIUM / HIGH / CRITICAL
- task_kind: general / mechanical / visual
- failure fingerprint count
- optional profile override + reason

默认执行主线：

TRIVIAL/LOW → coding-economy → 首选 GLM-5.1
SIMPLE/LOW → coding-fast → 首选 GLM-5.3-Flash
STANDARD + LOW/MEDIUM → coding-standard → 首选 GLM-5.2
HIGH risk 或 COMPLEX（但非 CRITICAL）→ coding-complex → 首选 GLM-5.3
CRITICAL complexity/risk → coding-critical → 首选 GPT-5.6 Sol

HIGH/CRITICAL risk 的独立 Review 使用 review-critical，首选 GPT-5.6 Sol。

GPT-5.6 Luna/Terra/Sol 和 GLM-5.1/5.2/5.3/5.3-Flash 均通过 Profile candidate 参与，不直接写入项目级 Task Board。Router 选出候选后必须经过本地 route preflight；CLI/version、非敏感配置指纹或 probed_models 记录变化时，自动执行必须停止并要求重新做真实模型 probe。

Router/Preflight 不是建议项。进入 Worker 前必须把 resolved_execution / resolved_review、preflight command、exit code 与 evidence 写入 Execution Request。delegated Worker 的实际 profile/backend/model/effort 必须和 resolved_execution 完全一致，否则 Contract Gate 失败。Controller 默认不得跳过 Router 自己编码；只有显式 controller_worker_override 才允许。

## Gate

Project Start / Plan Approval Gate：复杂/跨系统/高风险新项目，或任何新功能/实质性范围变化，必须先展示与规模相称的计划并取得明确用户确认。

FULL Design Baseline Gate：FULL 项目在计划确认后完成 PRD、适用的原型、架构/API 契约与分阶段计划；用户确认该设计基线前不得开始功能代码。门禁字段与 N/A 规则见 `policies/PROJECT_START_GATE.md`。FAST/STANDARD 只需一次按规模裁剪的计划确认。

Route Gate：resolved route + route_preflight PASS + 真实执行证据。

Task Gate：真实 Worker invocation + 命令验证 + 语义检查 + 无未解释回归。

Independent Review：Worker 之后使用独立 Session；Reviewer 必须与 resolved_review 一致并记录真实 invocation evidence；有兼容候选时优先不同 backend/model family。

Stage Gate：所有 Task 通过、集成检查通过、文档/状态更新。

Phase Gate：阶段目标、架构约束、风险和用户验收标准满足。

Gate 失败则回到修复，不得以“基本完成”越过。

## 模式

FAST：单点、低风险、可在一个上下文完成；快速分析→一个简短 Task→实现→合并验证与 Review Gate。计划可直接在对话中展示，除必需的 Gate、Request/Result 证据外不创建 Phase/Stage 文档或复制完整日志。

STANDARD：多文件但目标和边界清晰；默认只需要一个简明 Scope/Spec + Task Contract + 验证/Review。只有出现多组依赖任务、跨模块集成、长周期交付或明确阶段 Gate 时才展开 Phase/Stage。

FULL：高复杂度、高风险、跨系统或长期项目；完整需求、架构、依赖/风险、Phase/Stage 计划、分阶段集成、发布审查和回顾。

delegated_worker 接收到上层已拆好的 Task 时，不因 FULL 模式自动接管整个项目，只在当前 Task 内使用足够的规划深度。

## 上下文与恢复

当前任务优先，其次是相关源码、契约、最近 Review，再是架构和需求，最后才是历史。上下文不足时保存 checkpoint，切 Session；不要凭记忆继续。

恢复依据 Git HEAD、dirty state、checkpoint 和验证结果，Session 本身不是真源。没有 Git 时明确记录无 Git 基线并使用文件差异。

## 失败与升级

默认 max_retries=2，因此一个 Task Revision 最多是首次执行 + 2 次重试。首次失败记录 fingerprint；第 1 次 retry 保留当前 Profile 并基于新证据修复；同一 fingerprint 再次失败后，第 2 次 retry 才按 escalation 升级。环境、权限、需求歧义不应通过“换更强模型”掩盖。换 Session、模型或 Executor 不重置同一 fingerprint 的失败计数。Retry Budget 耗尽或出现高风险停止条件时进入 NEEDS_HUMAN。

## 人工决策

可逆的读、分析、测试和项目内编辑通常可自动继续，但 Project Start / Plan Approval Gate 是显式人工检查点：命中 Gate 条件的新项目在用户确认计划前不得开始业务代码 Implementation。对尚未授权的删除/覆盖重要数据、外部发布、付费资源、权限或凭据变更、破坏性迁移、改变范围或无法判断的业务取舍，同样必须询问用户。

已有授权不重复确认，明确人工检查点始终保留；Gate 是验证边界，不是重复许可。


## Execution clarifications

- **Plan approval:** For each new functional request or material scope change, show a plan scaled to the work, set explicit_plan_approval_required=true, and wait for explicit approval before implementation. Approval covers the stated scope; do not ask again at every Task Gate. Keep read-only investigation and plan preparation moving before approval.
- **Goal alignment:** At Task start and each Stage/Phase Gate, compare the work and proposed next step with the user's goal, approved scope, non-goals, and mapped acceptance criteria. Stop implementation when a change would redirect the product outcome; explain the mismatch and present a revised plan for approval.
- **Testing cost:** Run the smallest relevant check for each Task or coherent change set, not for every tiny edit. After a failure, rerun the failed check and the regression checks for affected paths. Run the full suite and end-to-end checks at Stage/Phase integration Gates and release acceptance. Choose additional checks by risk and record what was and was not run.
- **Skill discovery:** At intake, check the skills available in the current execution environment for a direct match to the task (for example frontend, backend, architecture, or security). Read and use only relevant skills; record the skill and purpose in result handoff_notes or the Task retrospective. A missing skill is not a reason to invent one.
- **Ponytail review:** Run Ponytail only when the user explicitly requests it. Record actionable findings without duplicating verification logs.
- **Retrospective:** At Stage/Phase Gates record concise lessons and link existing evidence. For a standalone FAST task, include a short note in its result only when there is a reusable failure or improvement; do not create a separate retrospective file by default. Promote a lesson to shared policy only after it is supported by evidence and authorized.
- **Agent handoff:** Every handoff must include the approved project goal and scope, current Task Contract and allowed paths, relevant architecture/decisions, current workspace and dirty-state facts, required checks, prior failure fingerprints/retry count, and the exact next action. The receiving agent verifies these against current files before editing. Do not rely on chat history alone.
- **Frontend/backend layout:** When a project has both, keep UI code under `frontend/` and server/API/domain code under `backend/`; define their API contract and startup/build checks before implementation. Do not place frontend and backend implementation in the same source directory.

Model bindings and routing policy are intentionally unchanged by this clarification.
