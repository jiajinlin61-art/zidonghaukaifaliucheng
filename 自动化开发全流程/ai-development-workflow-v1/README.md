# Universal AI Development Workflow V1

日常使用统一从根目录 README.md 开始。复制出的 starter-project 使用独立的轻量规则，不依赖本包位于固定位置；本页以下的 Router、Preflight 和 Execution Contract 机器门禁仅适用于明确启用完整规则包且工具可用的项目。

本包现在同时支持：

- standalone_master：Codex/其他主控直接管理整个项目。
- delegated_worker：接收外部 Project Controller（例如 GPT-TaskBoard）给出的一个 Task Contract，只负责该 Task 的路由、实现、Debug、Review 和执行结果回传。

核心材料：

- starter-project/：业务项目骨架与自包含 AGENTS 规则。
- DEVELOPMENT_WORKFLOW.md：整体流程。
- PROJECT_EXECUTION_RULES.md 与 policies/：执行约束。
- routing/MODEL_BINDINGS.yaml：Profile 到 Codex/Claude Code 及具体 GPT/GLM 模型的候选绑定。
- roles/：Worker、Debugger、Reviewer 职责。
- templates/PROJECT_START_GATE.yaml：复杂/跨系统/高风险新项目在业务代码开始前的计划确认门禁。
- templates/EXECUTION_REQUEST.yaml：上层控制器交给执行层的 1.3 请求，包含 project start gate、task revision、attempt、baseline、scope、resolved execution/review route、preflight、验收/验证映射、retry 和 stop conditions。
- templates/EXECUTION_RESULT.yaml：执行层返回上层的 1.3 结果，记录真实 Worker/Reviewer invocation、独立 Review 和项目集成边界。
- tools/project_start_gate_validate.py（位于仓库根目录）：计算并校验开发计划确认 Gate，未批准时可硬阻断 Implementation。
- tools/execution_contract_validate.py（位于仓库根目录）：区分 template/actual 模式，校验治理 Gate、resolved route、Worker/Reviewer 实际执行证据、scope、验证覆盖、Reviewer 独立性、失败指纹和状态一致性。
- tools/model_router.py（位于仓库根目录）：确定性路由参考实现。
- tools/route_preflight.py（位于仓库根目录）：执行前检查当前 CLI/version、非敏感配置指纹和模型探测记录是否仍匹配。
- CODEX_MASTER_PROMPT.md 与 prompts/：独立主控或分步执行时使用的请求。
- templates/：按项目复杂度选用的文档模板，不要求全部填写。
- WORKFLOW_MANIFEST.yaml：工作流版本、运行形态、模式、角色与 Profile 索引。

当前默认路由重点覆盖 GPT-5.6 Luna/Terra/Sol，以及 Claude Code 下的 GLM-5.1/5.2/5.3/5.3-Flash。模型是物理 Binding；Task 与角色优先引用 Profile，避免把项目流程绑定到某个固定模型版本。

小改动使用 FAST，常规跨文件功能使用 STANDARD，复杂或高风险工作使用 FULL。明确启用本完整规则包的项目，命中 Project Start Gate 时必须先展示计划并取得明确用户确认；实现 Task 必须真实运行 Router/Preflight 并调用 resolved Worker，Controller 不得静默代替 Worker。UADS 独立自动执行器仍未完成；现阶段由已有 AI 开发助手和本地 CLI 执行这些硬门禁。


## Plan confirmation and delivery checks

For every new functional request or material scope change, prepare a plan sized to the work, set explicit_plan_approval_required=true, and wait for explicit approval before implementation, including FAST tasks. A FAST plan may live in the conversation; keep one concise task record and link existing evidence instead of duplicating logs. Read the entry rules, current task, state, and relevant code first; load policies and templates only when needed. See `policies/PROJECT_START_GATE.md` and `DEVELOPMENT_WORKFLOW.md` for the remaining gates. Model routing and bindings are unchanged.
