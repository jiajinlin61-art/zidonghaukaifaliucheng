# AGENTS.md — Agent Handoff

本文件是所有开发 Agent 的第一入口。第一次接手项目时按顺序阅读：

1. `README.md` — 产品定位、运行与文档导航。
2. `docs/status.md` — 当前真实状态和唯一 NEXT。
3. `docs/roadmap.md` — 阶段顺序与阶段目标。
4. `docs/task-board.md` — 当前任务、依赖、Owner、Claim、边界和集成状态。
5. `docs/development-plan.md` — 当前 Task Revision 的详细执行合同。
6. `docs/needs-decision.md` — 等待用户决定的问题、阻塞范围和恢复条件。
7. 当前 Task 指向的 architecture/spec/ADR/模块文档。

如果文档冲突，以本文件规定的权威职责为准；不要用聊天记录覆盖磁盘和 Git 的当前状态。

## 1. 权威职责

```text
docs/status.md            当前阶段 / 当前事实 / 唯一 NEXT
docs/roadmap.md           阶段顺序 / 阶段目标 / Stage Gate
docs/task-board.md        Task / Revision / Claim / Owner / 依赖 / Allowed Paths / Acceptance
docs/development-plan.md  当前 Task Revision 的完整执行合同
docs/needs-decision.md    等待用户决定的问题、阻塞范围与恢复条件
Git                       代码、branch、worktree、commit 的真实状态
Tests                     完成证据
Execution Result/checkpoint 当前 attempt、route、失败计数、执行/Review 证据
```

如果项目接入独立 AI 执行工作流，Task Contract 还提供 Task Revision、Complexity / Risk / Task Kind 作为路由输入。具体 Backend、Model、Effort 和 attempt history 属于执行层证据，不写死在 Task Board。delegated_worker 不得更新项目级 NEXT、Roadmap 或 DONE。

## 2. 角色

### Coordinator

- 检查当前阶段与依赖，只领取 `READY` Task。
- READY→IN_PROGRESS 的领取临界区先获取 GPT-TaskBoard Coordinator 原子锁；锁只覆盖“重读状态→写 Claim→提交协调状态→再核对”，不跨整个 Task 执行。
- 为每个 Task Revision 固定一个 Owner、Claim ID、Claimed At、branch、worktree 和 Base Commit；同一 Revision 同时只允许一个有效 Claim。
- 明确 Allowed Paths、Forbidden Paths、带稳定 ID 的 Acceptance 与 required validation checks。
- 维护 `docs/task-board.md`；共享接口未稳定前不释放依赖任务。
- 领取协调提交后重新读取 Task Board 与 Git，确认 Claim 一致后释放 Coordinator 锁；若锁遗留，不按时间自动偷取，先核对 Git/TaskBoard 后按原 Claim ID 显式 break。

### Worker

- 只实现指定 Task ID + Revision，只在自己的 worktree 工作。
- 遵守 Allowed Paths；需要越界时停止并说明原因。
- 不直接修改 status、roadmap、task-board 等全局共享状态。
- 完成代码、测试、必要模块文档和 Git commit。
- 若 Worker 由独立执行工作流承载，必须返回 attempt identity、实际 route、按 required check ID 的验证证据、真实 changed_paths、failure fingerprint 和 remaining risks；不得自行领取下一项目级 Task。

### Integrator

- 串行 review Worker commit，一次只集成一个任务。
- 检查 scope、架构、数据安全、测试和文档。
- 合入 `main` 后重新验收，再更新 Task 和阶段状态。
- 集成失败时保留 branch/worktree/commit 和证据；不把失败 merge 当成重新实现任务的理由。

同一 Agent 可以依次承担三个角色，但不得省略对应检查。

## 3. Git / Worktree

```text
一个 Task Revision = 一个有效 Claim + 一个 Owner + 一个 branch + 一个 worktree
```

- Worker 禁止直接在 `main` 开发。
- 新依赖任务必须基于前置任务集成后的最新 `main` 创建。
- 不覆盖、reset、stash 或删除用户和其他 Agent 的未提交工作。
- Coordinator/Integrator 可以在干净的 `main` 维护协调状态文档；业务修改仍在 Task worktree 完成。
- 项目的实际 merge/rebase/cherry-pick 策略以 README 或开发文档为准。
- 清理 branch/worktree 前必须确认目标 commit 已进入 main、main 验收通过且 Task Board 已同步。

## 4. 默认共享文件

Worker 默认只读：

```text
AGENTS.md
README.md
docs/status.md
docs/roadmap.md
docs/task-board.md
docs/needs-decision.md
依赖锁文件
全局配置和公共 schema
```

确需修改时，必须在 Task Allowed Paths 中明确授权，或交给 Integrator 接线。

## 5. DONE

Task 只有同时满足以下条件才能进入 `DONE`：

1. 实现满足 Acceptance。
2. Task 范围测试通过。
3. 必要文档同步。
4. Task branch 已提交。
5. 独立 Review 通过。
6. Integrator 已把目标 commit 合入 `main`。
7. `main` 上必要验收通过。
8. Task Board、status 与 Git 状态一致。

Execution Result 的 `READY_FOR_REVIEW` / `REVIEW_PASSED` 都不等于项目级 `DONE`。

## 6. Worker Handoff

```text
Task: <TASK_ID>
Revision: <REV>
Attempt: <ATTEMPT_ID>
Status: READY_FOR_REVIEW
Branch: <BRANCH>
Commit: <HASH>
Changed:
- ...
Tests:
- command / exit code / evidence
Notes:
- Integrator 接线事项
- 已知风险 / blocker
```

## 7. 停止与阻塞范围

- Task 级 blocker：只阻塞当前 Task 和依赖它的任务；无关 READY Task 可继续。
- Stage 级 blocker：停止该 Stage 的相关任务；不影响无依赖的其他 Stage。
- Project 级 blocker：停止整个项目推进。
- 明确人工检查点按其声明的 scope 停止。

需要用户决定时，创建 `ND-xxx`、记录 `Block Scope: TASK / STAGE / PROJECT`、将相关 Task 标记为 `BLOCKED` 并写清恢复条件。不要因为一个 Task 等待用户就自动停止所有无关工作。
