# <PROJECT_NAME> — Development Plan

> 本文件保存复杂 Task 的完整执行合同。Task Board 只保留摘要、依赖和状态。

## 使用方式

- Worker 开始前读取本文件中对应 Task。
- 输入输出、公共接口或验收不清晰时，不开始实现。
- Task Board 与本文件冲突时，先由 Coordinator 修正文档，不自行选择。
- 若接入外部执行工作流，本文件提供 Task Contract；物理模型选择属于下游执行层，不属于项目事实来源。

## Task P1-01 — <标题>

### Outcome

<本任务完成后可以观察到的结果。>

### Non-goals

- <本任务明确不实现的内容>。

### Gate

- <必须已经满足的依赖、阶段或人工验收>。

### Routing metadata

```text
Task Revision: 1
Complexity: STANDARD
Risk: MEDIUM
Task Kind: general
Execution Profile: auto
Review Profile: auto
Profile Override Reason: —
Max Retries: 2
```

说明：

- Complexity：`TRIVIAL / SIMPLE / STANDARD / COMPLEX / CRITICAL`。
- Risk：`LOW / MEDIUM / HIGH / CRITICAL`。
- Task Kind：`general / mechanical / visual`。
- Task Revision 变化表示执行合同本身发生了语义变更；旧 attempt 不得冒充新 revision 的结果。
- 默认让执行层根据 Complexity/Risk 自动选择 Profile。
- 只有存在明确原因时才填写 Profile Override；override 只能保持或提高最低能力，不能降低风险要求。
- Max Retries 表示首次执行之后允许的额外重试次数；默认 2，即最多 3 次 attempt。
- Task Contract 不写死具体模型 ID。

### Inputs and outputs

**Inputs**

- <已有接口、数据、fixture、规格>。

**Outputs**

- <新能力、artifact、状态或测试证据>。

### Reuse

- <优先复用的成熟库、SDK、现有模块或项目能力>。

### New glue

- <必须自行编写的项目接线、Adapter 或转换层>。

### Allowed Paths

```text
<path/**>
<tests/**>
```

### Forbidden / shared paths

```text
AGENTS.md
README.md
docs/status.md
docs/roadmap.md
docs/task-board.md
依赖锁文件
```

### Public interfaces and migrations

- <新增/修改的 API、类型、schema、CLI 或配置>；
- <兼容、迁移或回滚要求；没有则明确写“无”>。

### Implementation order

1. <先打通的最小接口或测试>。
2. <核心实现>。
3. <接线和错误处理>。
4. <文档与验收>。

### Acceptance

```text
A1: <行为结果>
A2: <失败/边界结果>
A3: <用户数据或安全不变量>
```

### Required validation checks

每个 Acceptance ID 必须至少被一个稳定 Check ID 覆盖；纯语义验证必须在合同中明确声明，不允许 Worker 临时用“looks fine”替代命令要求。

```text
V1 command  → [A1, A2]  <真实测试/类型检查/构建命令>
V2 semantic → [A3]      <明确的语义核验标准>
```

若没有合适命令，使用 `semantic` check 并写清 criterion；若同时需要命令与语义检查，使用 `mixed`。

### Stop conditions

- <需要停止而不是猜测的条件>。

### Rollback and handoff

- <如何回滚>；
- <Worker 必须交付的 commit、测试结果和 Integrator 接线说明>。
- <若使用外部执行工作流，必须返回实际 role/profile/backend/model、验证证据、remaining risks；这些是本次执行证据，不成为项目级永久模型绑定。>
