# Project Rules — Workflow V1（2026-09-18 规范修订）

本文件包含新项目所需的最小规则，可独立于外部工作流包使用。用户当前明确指令优先；保留适用的项目约束。仅复制本目录时执行下述轻量流程；项目明确启用完整规则包时，再执行其中的路由、预检与 Execution Contract 1.3。

- 先读取 Brief/需求文档、`.ai-dev/PROJECT_START_GATE.yaml`、当前状态、计划、相关代码和已有改动。低风险单点工作用 FAST；常规跨文件用 STANDARD；跨系统或高风险用 FULL。STANDARD 默认使用简明 Scope/Spec + Task Contract；只有多组依赖、跨模块集成、长周期交付或明确阶段 Gate 才展开 Phase/Stage。FULL 使用 Phase → Stage → Task。
- 新项目命中 FULL、COMPLEX/CRITICAL、HIGH/CRITICAL risk、跨系统、架构变更或用户明确要求先确认计划时，必须先完整读取需求、形成架构和开发计划并展示给用户；用户明确确认并记录 approval_ref 前，`implementation.allowed=false`，禁止进入业务代码 Implementation。
- 每个 Task 写清 ID、目标、允许修改的范围、输入、验收命令、非目标和停止条件。输入与路径边界必须验证，不能吞掉错误或以简化为由省略必要的安全措施。
- 已授权且范围明确的工作自动继续。Task/Stage/Phase Gate 是质量检查，不是重复许可；明确人工检查点必须停。尚未授权的破坏性操作、外部发送/发布、付费、权限或凭据变更，以及无法推断的业务取舍，先给出具体影响再询问；不重复索要已有授权。
- 修改后检查差异，执行项目现有验证并核对需求、边界和回归。零测试不等于通过；纯文档任务可记录适当的替代核验。独立 Review 由另一个审查过程或人完成，作者的成功声明不作为证据；不得虚报测试或审查。
- Stage 检查所有 Task 和集成路径，Phase 检查阶段目标与用户验收条件；FAST 可以合并 Gate。失败时在授权内修复，未通过不得进入依赖它的工作；遇范围变化或显式停止条件再暂停。
- 失败记录稳定 fingerprint（task revision、error code、归一化错误、失败命令/接口）；model、backend、session、commit 属于 attempt context，不进入 fingerprint。默认最多 2 次 retry，即首次执行 + 2 次重试；第 1 次 retry 保持当前 Profile，同一 fingerprint 再失败后第 2 次 retry 才升级。没有新证据、预算耗尽或出现数据损失风险时停止并报告，换会话/模型/Executor 不能重置计数。
- 保护用户已有修改，不擅自回滚或清理。记录 Git HEAD 和 dirty state；没有 Git 时明确写“无 Git 基线”，改用文件差异，不编造提交号。
- standalone_master 模式下，在验收、关键决定、阻塞变化或中断时更新 `.ai-dev/CURRENT_STATE.md` 和 `.ai-dev/CHECKPOINT.md`。如果项目由外部 TaskBoard 作为 Project Controller，`.ai-dev` 只记录当前执行 attempt、证据和恢复线索，不维护第二份项目 NEXT/Roadmap/DONE。恢复时核对当前文件、Git 和证据；重启不清除人工阻塞，旧会话不是事实来源。
- 仅使用本 starter 时，按任务难度和用户指定选择当前可用模型，记录实际执行者、验证结果和审查证据；不得声称运行了未复制的 Router、route_preflight 或 Execution Contract 校验。需要严格的模型路由与机器门禁时，先明确启用完整规则包，核对工具、模型绑定和可执行环境，再按其规则执行。
- 独立 Review 由不同会话或人完成，保留审查结论与依据。使用完整规则包时，Reviewer 还须符合 resolved_review，Controller/Worker 的职责边界以该包的 Execution Request 为准。无法满足所选模式的必需门禁时说明原因并停止相关执行，不静默降级。用户明确指定的模型优先。


## Additional project workflow rules

- Before implementing any new functional request or material scope change, show a task-sized plan, set explicit_plan_approval_required=true, and wait for explicit user approval, including FAST work. Once approved, proceed through that scope without repeated permission requests.
- Keep the user's approved goal, non-goals, and acceptance criteria in Task Contracts; check alignment at Task start and each Stage/Phase Gate. Pause implementation if it begins to redirect the intended outcome.
- Test each coherent Task/change set with the smallest relevant checks. After a failure, rerun the failed check and affected regressions; run the full suite and end-to-end flow at integration/release Gates.
- At intake, use a skill only when it directly helps the task or the user requests it; record any invoked skill. Run Ponytail review only when the user explicitly requests it.
- At Stage/Phase Gates and standalone task completion, write a concise retrospective linked to request/result/review evidence.
- Agent handoffs include approved goal/scope, Task Contract, allowed paths, architecture decisions, current workspace state, checks, retry/failure history, and next action. Verify the live workspace on receipt.
- Projects with UI and server code use separate `frontend/` and `backend/` roots, with an explicit API contract and separate run/build checks.
