# <PROJECT_NAME> — Needs Decision

> 只记录必须由用户决定、会阻塞开发的产品或架构问题。普通 bug、实现细节和普通依赖不写入本文件。

## 1. 当前待决策

当前没有 OPEN 的待决策问题。

## 2. 使用规则

遇到需要用户决定的问题时：

1. 创建 `ND-xxx`。
2. 标记 `Block Scope: TASK / STAGE / PROJECT`，并把对应范围设为 `BLOCKED`。
3. 写清恢复条件和受影响的依赖任务。
4. 保存当前安全进度；只停止被该决策阻塞的范围。无关 READY Task 可继续。
5. 用户决定后将结论同步到 Task/spec/ADR，再标记 `RESOLVED`。

阻塞语义：

- TASK：只阻塞当前 Task 和依赖它的任务。
- STAGE：阻塞该 Stage 的相关任务；无依赖的其他 Stage 可继续。
- PROJECT：停止整个项目推进。

## 3. 条目模板

```markdown
## ND-001 — <问题标题>

**Status:** OPEN
**Related Task:** <TASK_ID>
**Block Scope:** TASK
**Raised:** YYYY-MM-DD

### 问题

<需要用户决定什么。>

### 为什么需要决策

<为什么不能从现有 spec/architecture/ADR 推导。>

### 可选方案

#### A. <方案名称>

- 优点：
- 缺点：
- 影响：

#### B. <方案名称>

- 优点：
- 缺点：
- 影响：

### Agent 推荐

<推荐及理由。>

### 恢复条件

<用户做出什么决定后恢复哪个 Task/Stage/Project；列出可继续的无关工作。>

### Decision

等待用户决策。
```

状态：`OPEN / RESOLVED / SUPERSEDED`。
