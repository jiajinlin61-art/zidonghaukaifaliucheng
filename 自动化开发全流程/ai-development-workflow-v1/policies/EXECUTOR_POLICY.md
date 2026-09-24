# Executor Policy

Project Controller 默认承担项目级目标、架构、计划、路由、验收和状态；Worker Executor 承担实际实现。Claude Code 默认承担常规到复杂编码 Worker；Codex/其他 backend 只在 Router 选择、fallback 或显式 override 时执行对应 Worker。

## Controller / Worker 隔离

Controller 不得因为“自己也能写代码”而跳过 Model Router 直接实现 routed Worker task。每个实现 Task 在进入 Worker 前必须：

1. 具有通过 Project Start Gate 的治理引用（APPROVED 或 NOT_REQUIRED）；
2. 生成 Execution Request 1.4；
3. 运行 model_router；
4. 运行 route_preflight；
5. 把 resolved_execution / resolved_review 和 preflight 证据写入 Request。

默认 `controller_worker_override.allowed=false`。只有用户明确要求 Controller 直接实现，或所有兼容 Worker backend 均不可用且需要受控 fallback 时，才允许设置 true，并记录具体 reason。不得用 override 隐式降低 Complexity/Risk 所需能力。

## Worker 执行证据

Worker 返回结果必须记录：

- 实际 profile/backend/model/effort；
- execution_mode；
- 独立 session；
- invocation.command / exit_code / evidence；
- changed paths；
- verification evidence。

在 delegated 模式下，Worker 实际 route 必须与 Request.resolved_execution 完全一致；若 Controller 暴露稳定 session id，Worker session 必须不同。

## Review

Reviewer 使用 Request.resolved_review，必须是独立 Session。模型 Reviewer 返回 backend/model/effort/session 和真实 invocation evidence。作者自审不能替代 Independent Review。

Executor 成功只表示 Worker 或 Review 层完成；项目级 Integration/DONE 仍由 Project Controller / Integrator 决定。换 Executor、Model 或 Session 不能重置同一 failure fingerprint 的失败计数。