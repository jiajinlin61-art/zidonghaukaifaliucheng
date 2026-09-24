# GPT-TaskBoard 教程

这套教程把两件事连成一个可验证的闭环：

1. 用 AgentDock 把网页版 ChatGPT 安全连接到自己的电脑。
2. 用项目文档、任务板和 Git，让 GPT 按已经确定的计划持续开发。

如果项目还接入独立的 AI 开发执行工作流，GPT-TaskBoard 只负责项目级状态、依赖、READY/BLOCKED/DONE 与最终 Gate；具体 Worker/Reviewer、模型 Profile、Codex/Claude Code 和失败升级由下游执行层负责。两层之间使用 Execution Request/Result 1.2 交接，不维护第二套项目事实来源。READY→IN_PROGRESS 的领取临界区使用短时项目级 Coordinator 原子锁，避免两个 Agent 同时写入不同 Claim。

建议严格按顺序阅读。先确认 GPT 能真实读取电脑上的文件和 Git，再引入自动领取任务、外部执行层与定时唤醒。不要在连接尚未验证时直接授权它修改重要项目，也不要一开始就创建定时任务。

## 学习路径

### 第一步：连接电脑

阅读 [安装 AgentDock 并连接网页版 ChatGPT](tutorials/01-agentdock-mcp-and-web-chatgpt.md)。

完成标准：

- AgentDock 本机服务正常；
- 网页版 ChatGPT 已通过 OAuth 连接公网 MCP 地址；
- GPT 能完成一次真实只读调用；
- GPT 能在专门的测试目录完成一次受控写入；
- 凭据没有进入 Git、截图或聊天记录。

### 第二步：先手动跑通开发闭环

阅读 [任务板与定时自动开发](tutorials/02-task-board-and-scheduled-development.md)，再查看 [虚构笔记应用示例](examples/note-app-walkthrough.md)。

已有项目使用 [接入工作流 Prompt](templates/prompts/adopt-workflow.md)，让 Agent 优先复用项目已有文档；新项目可以从 [templates/project/](templates/project/) 复制最小模板。

完成标准：一个小型 `READY` Task 已经经过领取、独立 worktree、开发、测试、提交、合入 `main`、main 复验和状态文档同步，最终进入 `DONE`。

如果项目使用独立执行工作流，再用 [Delegate Task Prompt](templates/prompts/delegate-task.md) 验证一次：TaskBoard 只提供 Task Contract 与 Complexity/Risk，下游返回实际执行 route、测试和 Review 证据，Project Controller 再决定 Task 状态。

### 第三步：再创建定时任务

手动闭环通过后，根据目标项目调整 [Scheduled Developer Prompt](templates/prompts/scheduled-developer.md)，再交给支持定时唤醒的 Agent 客户端。

定时器只负责把 Agent 再次叫醒。项目文档和 Git 才是跨会话的事实来源。

## 目录说明

```text
tutorials/        两篇按顺序阅读的教程
templates/project 可复制、可按项目调整的文档模板
templates/prompts 首次接入、Task 委派与定时开发 Prompt
tools/            Coordinator 原子锁工具
tests/            Claim 原子互斥回归测试
examples/         一个从 READY 到 DONE 的完整虚构案例
config-examples/  AgentDock 自建公网入口的脱敏配置示例
```

这些模板表达的是职责，不是强制文件结构。如果目标项目已经有 progress、plan、spec、ADR 或外部任务系统，优先维护现有事实来源，只补真正缺失的内容。

## 项目层与执行层的边界

GPT-TaskBoard 负责：

- 当前阶段与 NEXT；
- Task Revision、Claim、依赖、Owner、Allowed Paths、Acceptance；
- Complexity / Risk；
- BLOCKED / Decision；
- REVIEW / DONE 与 Stage Gate。

独立执行层负责：

- Worker / Debugger / Reviewer 角色；
- execution/review Profile；
- Codex / Claude Code 等 Backend；
- 具体物理模型和 effort；
- attempt identity、failure fingerprint、Retry/Escalation；
- 返回通过契约校验的 Execution Result；Worker 完成、Review PASS 与项目 DONE 分开表达。

TaskBoard 不应因为接入某个具体模型而改写项目计划；模型版本变化只应修改执行层 Binding。

## 安全边界

- AgentDock 会操作真实电脑，应只授予实际需要的目录和命令权限。
- 公网 MCP 必须使用 HTTPS 和认证。
- 不在仓库中保存 OAuth 密码、Bearer Token、签名密钥、SSH 私钥或真实部署配置。
- Agent 不覆盖、重置、暂存或删除用户与其他 Agent 的未提交工作。
- 产品方向、核心架构和重大技术路线仍由人决定。
