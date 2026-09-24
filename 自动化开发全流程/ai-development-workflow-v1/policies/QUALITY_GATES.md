# Quality Gates

验证分两类：命令型（test/lint/typecheck/build/安全检查）和语义型（需求、边界、错误处理、兼容性、可维护性）。没有命令时记录替代性自检，不虚报。

Project Start / Plan Approval Gate：复杂、跨系统或高风险新项目在 Implementation 前必须完成需求读取、架构/开发计划，并取得明确用户确认；未通过时 Implementation BLOCKED。FULL 项目还需要第二次设计基线审批（design_gate：PRD/原型/架构基线等设计制品，规则见 `PROJECT_START_GATE.md` 与 `tools/project_start_gate_validate.py`），通过前禁止功能代码。

Route Gate：Execution Request 1.3 必须包含确定性 resolved_execution / resolved_review，且 route_preflight.status=pass、exit_code=0、有 evidence。Worker 实际 profile/backend/model/effort 必须与 resolved_execution 一致，除非存在显式 controller_worker_override。

Task Gate：契约目标满足、真实 Worker invocation 有证据、可重复验证通过、diff 聚焦。

Independent Review Gate：Worker 之后使用独立 Session；模型 Reviewer 必须与 resolved_review 一致并有真实 invocation evidence。Reviewer session 与 Worker session 相同则失败。

Integration Gate：Task commit/diff 与目标基线一致，必要集成检查通过；delegated_worker 只返回证据，不声明项目级 DONE。

Stage Gate：仅在项目实际存在 Stage 时使用；要求该 Stage 的 Task Gate、集成路径和状态/文档一致。

Phase Gate：仅在项目实际存在 Phase 时使用；要求阶段目标、用户验收标准、风险处置和恢复/回滚信息完整。

FAST 可以合并 Task/Review/Integration，但不能绕过命中的 Project Start Gate。STANDARD 默认要求 Task + Independent Review + Integration；FULL 默认要求 Project Start（含 plan 与 design 两次审批）+ Route + Task/Stage/Phase + Independent Review + Integration。

任一 Gate 失败不得以“基本完成”继续依赖工作。