# Adopt GPT-TaskBoard Workflow

把 `<GPT_TASKBOARD_PATH>` 和 `<TARGET_PROJECT_PATH>` 替换成真实路径。若项目使用独立 AI 执行工作流，再提供 `<AI_DEVELOPMENT_WORKFLOW_PATH>`。

```text
把 GPT-TaskBoard 的持续开发工作流适配到 <TARGET_PROJECT_PATH>。

先阅读 <GPT_TASKBOARD_PATH> 的：
- README.md
- tutorials/02-task-board-and-scheduled-development.md
- templates/project/AGENTS.md
- templates/project/docs/status.md
- templates/project/docs/roadmap.md
- templates/project/docs/task-board.md
- templates/project/docs/needs-decision.md
- templates/project/docs/development-plan.md
- templates/prompts/scheduled-developer.md
- templates/prompts/delegate-task.md

然后进入目标项目，先阅读：
- AGENTS.md / agent.md（如果存在）
- README
- 已有 architecture / spec / ADR
- 已有 progress / status / roadmap / plan
- 已有 task / todo / issue system
- 当前目录结构
- git status
- git log
- git worktree list

目标项目自己的约定和真实 Git 状态优先。不要为了匹配 GPT-TaskBoard 强制复制固定文件名，也不要创建与现有文档重复的第二套事实来源。

至少确认目标项目能够明确表达：
1. 当前真实状态和当前阶段。
2. 后续阶段顺序和 Stage Gate。
3. 当前可执行的具体 Task。
4. 每个 Task 的 Revision、Status、Owner、依赖、Allowed Paths 和 Acceptance。
5. 每个可执行 Task 的 Complexity / Risk；复杂 Task 可在 development plan 中补 Task Kind。
6. READY → IN_PROGRESS 的 Claim ID / Claimed At / Base Commit 规则，以及同一 Revision 单有效 Claim 约束；领取临界区使用 GPT-TaskBoard `tools/coordinator_lock.py` 的短时项目级原子锁。
7. DONE 的定义和 main 验收要求。
8. 多 Agent 的 branch/worktree/Owner 与中断恢复规则。
9. 哪些问题必须由用户决定、Block Scope（TASK/STAGE/PROJECT）以及恢复条件。
10. 阶段完成后如何验收和释放下一阶段。

如果现有文档已承担这些职责，直接维护现有文档。只有职责缺失时，才参考模板创建最少数量的新文档。

Task 应小型、边界明确、可独立验收、依赖清楚。推荐状态：
BACKLOG / READY / IN_PROGRESS / REVIEW / BLOCKED / DONE。

DONE 默认至少意味着：
实现完成 + 测试通过 + Git commit + 集成 main + main 必要验收通过 + 状态文档同步。

多 Agent 默认采用：
一个 Task Revision = 一个有效 Claim + 一个 Owner + 一个 branch + 一个 worktree。
如果项目已有成熟规则，以项目规则为准。

如果接入 <AI_DEVELOPMENT_WORKFLOW_PATH>：
- GPT-TaskBoard 仍是项目级状态来源。
- Task Board 记录 Task Revision / Claim / Complexity / Risk，不写死具体模型 ID。
- 下游执行层负责 attempt identity、role/profile/backend/model、失败升级和独立 Review。
- 使用 Execution Request / Result 1.2；Acceptance 与 required checks 使用稳定 ID 映射，执行前后都以 actual 模式运行契约校验，并在 Worker 启动前运行 route preflight。
- Worker 完成只能到 READY_FOR_REVIEW；独立 Review PASS 后才能到 REVIEW_PASSED；项目级 DONE 仍由 Integrator 决定。
- 下游 Worker 不领取下一项目 Task，不更新项目级 NEXT/DONE。

需要用户决定的问题写入项目自己的 Decision Inbox，关联 Task，记录 Block Scope（TASK/STAGE/PROJECT）并标记对应范围 BLOCKED。Task 级 blocker 只阻塞当前 Task 和依赖它的工作；Agent 可以继续不受影响的 READY Task，但不能代替用户选择产品方向、核心 Domain、重要架构或重大技术路线。

完成适配后：
1. 检查文档之间是否矛盾。
2. 检查 Task 状态与 Git 是否一致。
3. 确保至少有一个 READY Task，或明确没有 READY 的原因。
4. 根据目标项目真实文档路径生成 Scheduled Developer Prompt。
5. 若接入独立执行层，确认 delegate-task Prompt 能从当前 Task 生成标准 handoff。
6. 更新必要的 README / architecture / status / roadmap。
7. 运行项目规定的文档和测试检查。
8. 审阅差异并提交 Git。

最终输出：
- 复用了哪些已有文档
- 新增了哪些必要职责
- 当前 READY Task
- Task 的 Complexity / Risk
- 定时 Prompt 的位置
- 执行层 handoff 位置（如启用）
- OPEN 决策问题
- 测试和 Git commit
```
