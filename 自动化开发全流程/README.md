# 自动化开发工作流：使用入口

现在可以使用的是由 AI 开发助手执行的工作流：读取需求 → 拆分任务 → 实现 → 测试 → 修复 → 验收 → 保存进度。它提供执行规则和项目模板，不会自行在后台运行或定时唤醒。

UADS 独立自动执行程序仍未实现；`python -m uads` 目前只输出版本号。使用下面的工作流不需要安装或运行 UADS。明确启用完整规则包时，实际 Worker 必须使用 Model Router 选中的可用 backend；默认 route 选中 Claude Code 时就必须真实调用 Claude Code，不能静默改成当前主控模型。

完整规则包包含 Project Start Gate、Model Routing 与 Execution Contract 1.3：复杂/跨系统/高风险新项目必须先展示开发计划并获得明确确认；Task 再按 Complexity / Risk 映射到能力 Profile。完整规则包的工具与模型配置位于本目录的 `tools/` 和 `ai-development-workflow-v1/routing/`；只复制 `starter-project` 时不包含这些工具，使用其独立的轻量流程。UADS Runtime 的 lease/heartbeat/timeout 仍是规格设计，不应描述成已运行能力。

## 1. 建立你的业务项目

复制整个 [starter-project](ai-development-workflow-v1/starter-project/) 文件夹到一个新的空目录，改成你的项目名。确认隐藏的 `.ai-dev` 文件夹也已复制。仅复制 starter 时按其轻量规则执行；如需完整规则包的机器路由和契约校验，应在项目中明确引用完整规则包并核对工具可用性。

这是你的业务项目目录。不要把本目录下用于开发 UADS 的 `.uads`、`src`、`tests` 或 `.venv` 一起复制过去。

如果已有业务项目，不直接覆盖它：让助手先读取现有规则和代码，比较模板中的 AGENTS 与状态文件，仅合并缺失内容，保留已有规则、计划、环境和修改。

## 2. 写清需求

在新项目 `docs/PROJECT_BRIEF.md` 中填写：

- 目标：要解决什么问题，给谁用。
- 范围内/范围外：要做什么、明确不做什么。
- 约束：使用环境、已有系统、不能改的内容、成本或权限限制。
- 成功标准：怎样操作、看到什么结果，才算做完。

不用写技术设计。不会填写时，可以把上述信息直接告诉助手，让它整理进 Brief；仍不明确且会影响结果的部分再询问你。

## 3. 启动开发

让 AI 开发助手在你的业务项目目录工作，把下面的请求发给它：

> 阅读本项目 AGENTS.md、docs/PROJECT_BRIEF.md、.ai-dev/PROJECT_START_GATE.yaml 和 .ai-dev/CURRENT_STATE.md，先核对现有代码、环境与修改。我授权你按 Brief 完成本项目范围内的开发、测试、修复和交付。先判断复杂度/风险和模式；需要计划确认时先展示计划，得到明确确认后再开始业务代码。仅复制 starter 时按轻量流程选择实际可用的执行者、验证并独立审查；明确启用完整规则包时再运行其模型路由、预检和契约校验。关键进展及中断前更新状态和 checkpoint。完成后提供可运行结果、启动方法、真实执行/测试/Review 证据及剩余限制。

助手应按任务连续推进，检查通过后进入下一个任务，必要时才请求你的决策。你需要提供其无法访问的业务信息，以及运行环境实际要求的权限。发布、付费等未授权动作不会因这段请求自动获得许可。

## 4. 中断后继续

在同一个业务项目目录中发送：

> 阅读本项目 AGENTS.md、.ai-dev/CURRENT_STATE.md、.ai-dev/CHECKPOINT.md 和当前计划，对照代码、文件变化与验证证据核实进度。保留未决人工请求和失败计数，从已核实的未完成工作继续，完成原来授权的范围。不要重复已完成工作；遇到明确人工检查点仍须停下。

状态文件是线索，当前代码与真实验证结果才是完成依据。没有后台调度器；助手停止或会话中断后，需要再次发起继续请求。

## 5. 怎样验收结果

要求交付真实可运行的程序、明确启动方法、实际执行的测试，以及未完成或未验证内容。复杂项目还需集成检查；纯文档任务记录适当的替代核验。不要把“测试零条”“只创建目录”或“计划已写好”视为业务完成。

## 其他文件的用途

| 内容 | 用途 |
|---|---|
| [starter-project](ai-development-workflow-v1/starter-project/) | 可独立使用的轻量项目骨架；不含完整规则包的路由工具 |
| [工作流规则包](ai-development-workflow-v1/README.md) | 可选的详细规则、提示词和模板 |
| [UADS 规格](SYSTEM_SPEC_V1_REV2.md)、[实施计划](IMPLEMENTATION_PLAN.md)、[Phase 0](PHASE_0_START.md)、[开发说明](docs/DEVELOPMENT.md) | 开发未来自动执行程序所需；日常使用工作流无需阅读 |

本目录自身不是业务项目模板，也尚未初始化 Git。保留的 `.uads` 是开发 UADS 的任务种子，不会被业务项目自动执行。

## 当前精简结构

```text
自动化开发流程/
├── ai-development-workflow-v1/   当前可直接使用的 AI 开发工作流
│   ├── policies/                 执行策略
│   ├── prompts/                  执行/Review/恢复提示
│   ├── roles/                    Worker/Debugger/Reviewer
│   ├── routing/                  Model Profile 与物理模型绑定
│   ├── starter-project/          新业务项目骨架
│   └── templates/                可选项目文档和 handoff 模板
├── .uads/                        未来 UADS Runtime 的计划和任务种子
├── src/uads/                     UADS 当前代码骨架
├── tests/                        工作流/UADS 回归测试
├── tools/                        bootstrap、测试入口和 Model Router
├── docs/                         开发说明与人类阅读指南
├── SYSTEM_SPEC_V1_REV2.md        UADS 设计基线
├── IMPLEMENTATION_PLAN.md        UADS 实施计划
├── PHASE_0_START.md              UADS Phase 0 入口
└── pyproject.toml                Python 包与开发依赖
```

已移除纯历史验收归档、空的 learning 日志模板和空运行结果目录；保留的 `.learnings/` 文件包含实际经验和待处理需求，不属于日常启动必读材料。

## 用户确认与执行方式补充

每个新的功能需求或实质性范围变化，都先给出与任务规模相称的开发计划，并等待用户明确确认后再开始功能实现，包括 FAST 小任务。FAST 计划可直接写在对话中；已批准范围内的修复和补测连续推进，不重复请求许可；若目标或范围改变，再提交修订计划确认。日常只读取项目规则、当前需求/状态和相关代码，其他策略与模板按需读取。具体执行要求见 ai-development-workflow-v1/DEVELOPMENT_WORKFLOW.md。

