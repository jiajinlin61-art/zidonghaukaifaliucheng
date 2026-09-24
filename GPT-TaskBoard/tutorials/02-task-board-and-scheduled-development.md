# 教程二：用任务板让 GPT 持续开发

开始本教程前，应先完成 [教程一](01-agentdock-mcp-and-web-chatgpt.md)：网页版 ChatGPT 已经能够通过 AgentDock 读取指定目录、查看 Git，并在测试目录完成受控写入。

这一篇解决另一个问题：GPT 已经能操作电脑以后，怎样让它每次都知道项目做到哪里、现在能做什么、什么才算完成，以及什么时候必须停下来找人决定。

## 1. 最小闭环

```text
读取项目文档 + Git
        ↓
恢复自己的未完成任务
        ↓ 没有可恢复任务
领取一个 READY Task
        ↓
独立 branch + worktree
        ↓
实现 / 测试 / 文档 / commit
        ↓
Integrator review + 合入 main
        ↓
main 重新验收
        ↓
Task → DONE，解锁依赖任务
        ↓
重新读取磁盘状态
```

定时器只负责把 Agent 再次叫醒。任务能否继续，必须由项目文档、Git、测试和当前工作区状态决定。

## 2. 六个层次各自负责什么

| 层 | 负责 | 不负责 |
|---|---|---|
| 网页版 GPT | 理解任务、调用工具、实现和汇总 | 不把聊天记忆当项目事实 |
| AgentDock | 文件、命令、Git、浏览器等本机能力 | 不决定产品方向或下一个任务 |
| 项目文档 | 当前阶段、路线、任务、边界、决策 | 不自动证明代码已经完成 |
| Git/worktree | 隔离修改、保存提交、支持 review | commit 不自动等于 DONE |
| Tests/Acceptance | 给出可重复的完成证据 | 不替代人工产品决策 |
| Scheduler | 定时唤醒 | 不绕过依赖、冲突和 BLOCKED |

核心原则：

> 项目文档和 Git 是事实来源，聊天记录不是。

## 3. 项目至少要表达哪些信息

文件名并不重要，但这些职责必须能被 Agent 明确找到：

| 职责 | 推荐文件 | 关键问题 |
|---|---|---|
| Agent 入口 | `AGENTS.md` | 先读什么、怎么协作、哪些不能改 |
| 当前状态 | `docs/status.md` | 现在做到哪里、唯一 NEXT 是什么 |
| 开发顺序 | `docs/roadmap.md` | 阶段如何推进、何时解锁下一阶段 |
| 执行任务 | `docs/task-board.md` | 现在有哪些 Task 可以领取 |
| 人工决策 | `docs/needs-decision.md` | 哪些问题必须等用户决定 |
| 任务合同 | `docs/development-plan.md` | 复杂 Task 的输入输出、边界和验收 |

已有项目可能使用 progress、plan、spec、ADR、GitHub Issues 或其他任务系统。先阅读并复用它们，不要为了套模板制造第二套互相冲突的事实来源。

## 4. Task Board 的最小格式

每个可执行任务至少包含：

```text
ID
Revision
Task
Status
Owner
Depends On
Allowed Paths
Acceptance
```

如果项目接入独立 AI 执行工作流，再补充 `Complexity`、`Risk`，复杂任务可在执行合同中增加 `Task Kind`。这些字段只用于下游能力路由，不把具体模型 ID 固化进 Task Board。

示例：

| ID | Task | Status | Owner | Depends On | Allowed Paths | Acceptance |
|---|---|---|---|---|---|---|
| N1-01 | 定义 Note contract | DONE | agent-a | — | `src/domain/**`, tests | contract tests PASS |
| N1-02 | 实现文件存储 | READY | — | N1-01 | `src/storage/**`, tests | create/read/reopen PASS |
| N1-03 | 接入 CLI | BACKLOG | — | N1-02 | `src/cli/**`, tests | CLI 集成测试 PASS |

此时只有 `N1-02` 可以领取。`N1-03` 已经规划，但依赖尚未完成。

## 5. 状态语义

```text
BACKLOG
   ↓ 依赖和阶段 Gate 满足
READY
   ↓ Coordinator 领取并固定 Owner
IN_PROGRESS
   ↓ Worker 完成任务分支验收
REVIEW
   ↓ Integrator 合入 main 并复验
DONE
```

异常路径：

```text
IN_PROGRESS / REVIEW
        ↓
     BLOCKED
        ↓ 恢复条件满足
IN_PROGRESS / REVIEW
```

- `BACKLOG`：计划存在，但当前不允许领取。
- `READY`：依赖、阶段 Gate 和共享接口都已满足。
- `IN_PROGRESS`：已有唯一 Owner 正在实现。
- `REVIEW`：任务分支已完成，等待或正在集成。
- `BLOCKED`：无法继续，必须写清阻塞原因和恢复条件。
- `DONE`：已合入 `main`，并完成 main 上规定的验收和文档同步。

“Agent 说写完了”或“分支测试通过”都不足以进入 `DONE`。

## 6. 一个任务一个 Owner、branch 和 worktree

多 Agent 协作时推荐：

```text
一个 Task Revision = 一个有效 Claim + 一个 Owner + 一个 branch + 一个 worktree
```

角色边界：

- **Coordinator**：检查依赖，领取/分配任务，维护 Task Board，指定 Task Revision、Claim ID、Claimed At、branch、worktree、Base Commit、Allowed Paths 和 Acceptance。同一 Task Revision 同时只允许一个有效 Claim。
- **Worker**：只在自己的 worktree 实现指定 Task，不直接修改全局状态文档。
- **Integrator**：串行 review、测试、合入 `main`，在 main 复验后更新任务状态。

同一个 Agent 可以依次承担三种角色，但不能跳过角色对应的检查。

### 领取任务

1. 确认 `main` 工作区干净，没有用户或其他 Agent 的未提交修改。
2. 生成唯一 Claim ID，使用 `tools/coordinator_lock.py` 获取短时项目级 Coordinator 锁。Git 项目锁写入共享 Git common-dir，因此所有 worktree 共用同一把锁。
3. 持锁重新读取 Task Board、main HEAD、worktree/branch/commit；只有 Task 仍为 `READY` 且没有其他有效 Claim 才继续。
4. Coordinator 把 Task 改为 `IN_PROGRESS`，填写 Revision、Owner、Claim ID、Claimed At、branch、worktree 和 Base Commit，并提交协调状态。
5. 提交后再次读取 Task Board / Git，确认 Claim 与预期一致；确认后释放 Coordinator 锁。
6. 只有 Claim 仍有效时，才基于最新 `main` 创建或恢复任务 branch/worktree。异常退出遗留的锁不能按时间自动偷取，必须先核对 TaskBoard/Git/worktree/commit，再用原 Claim ID 和明确 reason 显式 break。

状态协调可以由 Coordinator/Integrator 在 `main` 完成；业务实现禁止直接在 `main` 开发。

Claim 是任务领取身份；Coordinator 锁是短时领取互斥，不是 Task 生命周期 lease。锁只保护“重读 → 写 Claim → 协调提交 → 再核对”，Task 执行期间应释放。恢复时必须结合 Task Board、Git、worktree 和 commit 判断真实进度，不能只按聊天上下文重建。

示例：

```bash
git worktree add ../note-app-n1-02 -b codex/n1-02-file-storage main
```

### 中断后的恢复顺序

恢复时优先复用已有执行，不重新实现：

1. `IN_PROGRESS` 且 worktree/branch 存在、尚无 Task commit：恢复原 worktree 和 Claim。
2. Task commit 已存在但状态仍是 `IN_PROGRESS`：核对 commit 和测试后进入 `REVIEW`。
3. `REVIEW` 且 commit 未进入 main：从现有 commit 继续 Integrator review/集成。
4. commit 已进入 main，但 Task 仍未 `DONE`：只做 main 复验和状态修复，不重复 merge/实现。
5. main 已验收但 status/roadmap 未同步：只修复协调状态，再释放依赖 Task。
6. Task 标记执行中但 branch/worktree/commit 均无法定位：进入 `BLOCKED` 并记录恢复条件。

只有在目标 commit 已进入 main、main 验收通过且 Task Board 已同步后，才清理 branch/worktree。不能仅凭 `DONE` 文本删除执行现场。

### Worker 交付

Worker 完成后应返回：

```text
Task: N1-02
Revision: 1
Attempt: <attempt-id>
Status: READY_FOR_REVIEW
Branch: codex/n1-02-file-storage
Commit: <commit>
Changed:
- ...
Tests:
- <command> / <exit code> / <evidence>
Notes:
- 需要 Integrator 完成的共享接线
- 已知风险或 blocker
```

### 可选：把 Worker 交给独立执行工作流

如果项目使用独立 AI 开发执行层，Coordinator 仍然从 Task Board 领取 Task，但不要在 Task Board 中写死具体模型。项目层只提供：

```text
Task ID
Task Revision
Claim ID / Base Commit
Objective
Complexity
Risk
Task Kind
Allowed Paths / Forbidden Paths
Acceptance（稳定 ID）
Required Validation Checks（稳定 ID + acceptance_ids）
Stop Conditions
```

下游执行层负责选择 Worker / Debugger / Reviewer、Execution Profile、Backend、具体模型与 effort，并为每次执行分配 attempt_id。Execution Request/Result 1.2 必须通过 actual 契约校验，所选 route 还要通过本地 preflight。Worker 验证通过只返回 `READY_FOR_REVIEW`；模型 Reviewer 必须使用与 Worker 不同的 session，或使用有明确 reviewer_id/evidence 的人工 Reviewer，PASS 后才返回 `REVIEW_PASSED`。Execution Result 不能声明项目级 DONE，`project_integration` 必须由 Project Controller / Integrator 评估。

推荐边界：

```text
GPT-TaskBoard
  项目级状态 / READY / BLOCKED / DONE
        ↓ Task Contract
Execution Workflow
  Worker → Test/Debug → Independent Reviewer
        ↓ Execution Result
GPT-TaskBoard
  Integrator 复验 → REVIEW / DONE / BLOCKED
```

Task 的 Complexity / Risk 是路由输入，不是永久模型绑定。模型版本变化应只修改执行层配置。

### Integrator 验收

1. 检查 commit 和 diff 是否只包含 Task scope。
2. 检查架构边界、数据安全和兼容性。
3. 在任务 branch 运行验收。
4. 按项目规定合入 `main`。
5. 在 `main` 再次运行必要验收。
6. 更新 Task 为 `DONE`，同步 status/roadmap，并释放依赖任务。
7. 提交状态文档更新，再清理已完成的 worktree/branch。

## 7. 什么才算 DONE

默认最低标准：

```text
实现满足 Acceptance
+ 任务范围测试通过
+ 必要文档同步
+ Task branch 已提交
+ Integrator review 通过
+ 已合入 main
+ main 必要验收通过
+ Task Board 与 Git 一致
```

阶段完成比单个任务更严格。某阶段的 Task 全部 DONE 后，还要重新读取阶段验收标准，检查构建、集成测试、文档、Git 和人工 Gate，才能把阶段标记为完成。

## 8. 哪些问题必须交给人决定

以下情况进入 `needs-decision.md`：

- 产品行为需要重新决定；
- 核心 Domain 或数据语义要改变；
- 需要新增、推翻或修改重要架构决策；
- 存在多个合理方案，现有 spec/ADR 无法确定取舍；
- 继续实现等同于 Agent 代替用户选择重大技术路线。

普通 bug、已有文档能推导出的实现细节、局部可逆选择和普通依赖阻塞不进入 Decision Inbox。

产生人工决策时：

1. 创建 `ND-xxx` 条目。
2. 记录 `Block Scope: TASK / STAGE / PROJECT`，把对应范围设为 `BLOCKED`。
3. 写清问题、方案、影响、Agent 推荐、恢复条件和受影响依赖。
4. 保存当前安全进度。
5. 只停止被该决策阻塞的范围；TASK blocker 不妨碍无依赖关系的其他 READY Task 继续。

## 9. 接入已有项目

把本仓库路径和目标项目路径提供给 Agent，然后使用 [接入工作流 Prompt](../templates/prompts/adopt-workflow.md)。

Agent 应先检查目标项目已有的：

```text
AGENTS.md / agent.md
README
architecture / spec / ADR
progress / status / roadmap
task / todo / issue system
git status / log / worktree
```

只有缺少必要职责时，才参考 [`templates/project/`](../templates/project/) 增加小型文档。适配完成时至少要存在一个明确的 READY Task，或者明确记录为什么没有。

## 10. 先手动完成一个小任务

不要接入工作流后立刻创建每小时定时任务。先选择一个满足这些条件的 Task：

- 预计一次可以完整交付；
- Allowed Paths 清晰；
- 不需要重大产品或架构决策；
- 有自动化或可重复的 Acceptance；
- 能独立合入和回滚。

让 GPT 人工执行一轮完整闭环。重点观察：

- 是否先读文档和 Git；
- 是否真的领取而不是直接改代码；
- 是否使用独立 worktree；
- 是否遵守 Allowed Paths；
- 是否在 main 复验后才标记 DONE；
- 是否正确更新下一 READY Task；
- 遇到重大问题是否停下来。

完整案例见 [虚构笔记应用演练](../examples/note-app-walkthrough.md)。

## 11. 再创建定时任务

手动闭环通过后，根据目标项目的真实文档结构调整 [Scheduled Developer Prompt](../templates/prompts/scheduled-developer.md)。不要保留目标项目中不存在的路径。

每次唤醒必须重新：

1. 读取项目规则、状态、路线、任务和决策文档。
2. 检查 `git status`、`git worktree list` 和 `main` HEAD。
3. 优先恢复本 Agent 的 `IN_PROGRESS` 或 `REVIEW` Task。
4. 没有可恢复任务时才领取新的 `READY` Task。
5. 完成后重新读取磁盘状态，不凭上一任务的聊天上下文继续。

停止条件至少包括：

- 达到单轮 Task 数上限；
- 没有 READY 或可恢复任务；
- 存在覆盖当前可继续范围的 STAGE/PROJECT blocker，或所有 READY Task 都被 TASK blocker/依赖阻塞；
- 与其他 Agent 当前工作冲突；
- 当前可继续范围需要用户决定，且没有其他不受该 Block Scope 影响的 READY Task；
- Git 状态无法安全继续。

“没有任务”是正常停止，不是失败。Scheduler 下一次仍应从磁盘重新检查。

## 12. 验收清单

- 项目权威文档和阅读顺序明确；
- Task 至少有 ID、Revision、状态、Owner、依赖、Allowed Paths 和 Acceptance；
- 当前最多只有依赖已满足的任务处于 READY；
- 一个 Task Revision 同时只有一个有效 Claim、Owner、branch 和 worktree；
- Worker 不直接在 main 开发或修改全局任务状态；
- DONE 包含 main 集成和 main 复验；
- Decision Inbox 和恢复条件可追踪；
- 已人工跑通一个小型 Task；
- 定时 Prompt 已按目标项目结构调整；
- AgentDock 凭据没有进入项目文档。
