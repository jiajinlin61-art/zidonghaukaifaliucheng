# <PROJECT_NAME> — Main Task Board

<!-- project-stage: P1 -->

> 当前阶段：**P1 ACTIVE**。当前唯一可领取任务是 `P1-01`。

## 1. 执行规则

状态：`BACKLOG / READY / IN_PROGRESS / REVIEW / BLOCKED / DONE`。

- 只有 `READY` 可以领取；领取临界区必须先获得项目级 Coordinator 原子锁，再固定唯一 Owner、Claim ID、branch、worktree、Base Commit 和 Claimed At。
- Coordinator 锁只保护“重读状态 → 写 Claim → 提交协调状态 → 再核对”的短临界区，不覆盖整个 Task 执行；同一个 Task Revision 同一时间最多一个有效 Claim。
- 锁异常遗留时不得按时间自动偷取；必须先核对 Task Board/Git/worktree/commit，再用原 Claim ID 和明确原因显式 break。
- 依赖、阶段 Gate 和共享接口未满足时保持 `BACKLOG` 或 `BLOCKED`。
- Worker 遵守 Allowed Paths，不直接修改本文件。
- Task branch 完成并有真实 commit 后进入 `REVIEW`；合入 main 并复验后才进入 `DONE`。
- 重大产品/架构问题写入 `needs-decision.md`，并记录阻塞范围和恢复条件。
- `Complexity` / `Risk` 是下游执行层的能力路由输入；Task Board 不写死具体模型 ID。具体 Backend、Model、Effort、attempt 和失败升级由执行工作流负责。

## 2. Stage Gate

```text
P0 VALIDATED
  ↓
P1-01 → P1-02 → P1-03
                    ↓
                P1 VALIDATED
```

## 3. 当前任务

| ID | Rev | Task | Status | Owner | Depends On | Complexity | Risk | Allowed Paths | Acceptance |
|---|---:|---|---|---|---|---|---|---|---|
| P1-01 | 1 | <第一个可执行闭环> | READY | — | P0 VALIDATED | STANDARD | MEDIUM | `<paths>`, tests | <可重复验证的结果> |
| P1-02 | 1 | <依赖 P1-01 的任务> | BACKLOG | — | P1-01 | SIMPLE | LOW | `<paths>`, tests | <验收> |
| P1-03 | 1 | P1 release gate | BACKLOG | — | P1-02 | COMPLEX | HIGH | integration/release tests, docs | main 全部阶段验收通过；status/roadmap 同步 |

复杂度：`TRIVIAL / SIMPLE / STANDARD / COMPLEX / CRITICAL`。

风险：`LOW / MEDIUM / HIGH / CRITICAL`。

## 4. Coordinator NEXT

```text
NOW: P1-01 READY
BLOCKED BY DEPENDENCY: P1-02, P1-03
```

领取前先使用 GPT-TaskBoard 的 `tools/coordinator_lock.py` 获取项目级 Coordinator 锁。Git 项目默认把锁放在共享 Git common-dir 下，因此多个 worktree 看到同一把锁。

锁获取成功后，在同一个临界区内重新读取 Task Board 和 main HEAD，再填写并提交：

```text
Task Revision: 1
Owner: <AGENT_ID>
Claim ID: <TASK_ID>-r<REV>-claim-<UNIQUE_ID>
Claimed At: <ISO-8601>
Branch: codex/p1-01-<slug>
Worktree: <ABSOLUTE_WORKTREE_PATH>
Base Commit: <MAIN_COMMIT>
```

协调状态提交完成后重新读取 Task Board、main HEAD 和 worktree 列表。如果 Claim 与预期不一致，停止并保留证据。确认 Claim 成功后释放 Coordinator 锁，再创建/继续 Task worktree。异常退出导致锁遗留时，下一轮先恢复/核对原 Claim；不能自动创建新 Claim。

## 5. 中断恢复

恢复时以 Task Board + Git + worktree + commit +真实验证为准，按以下顺序判断：

1. `IN_PROGRESS`，worktree/branch 存在但没有 Task commit：恢复原 worktree，继续原 Claim；不要新建第二个 branch。
2. Task commit 已存在但 Task Board 仍为 `IN_PROGRESS`：核对 commit 和验证，进入 `REVIEW`；不要重新实现。
3. `REVIEW` 且 commit 尚未进入 main：Integrator 从现有 commit 继续 review/集成；集成失败时保留 branch/worktree 和证据。
4. Task commit 已进入 main，但 Task Board 仍未 `DONE`：在 main 复验并只修复协调状态；不要重复实现或再次 merge。
5. main 验收通过但 status/roadmap 尚未同步：只完成状态修复后再释放依赖任务。
6. Task 标记 `IN_PROGRESS/REVIEW` 但对应 branch/worktree/commit 均无法定位：标记 `BLOCKED`，记录恢复条件，不凭聊天记忆重建。

清理 branch/worktree 的前置条件是：目标 commit 已确认进入 main、main 验收通过、Task Board 已同步。不能仅凭 `DONE` 文本删除工作。

如果项目接入外部执行工作流，Coordinator 在领取后把当前 Task Revision 转成标准 Execution Request；执行层完成后返回带 attempt identity 的 Execution Result。Project Controller 仍然负责 Task Board 的 REVIEW/DONE/BLOCKED，不允许下游 Worker 自行领取下一个项目级 Task。
