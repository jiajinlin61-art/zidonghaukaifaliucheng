只执行当前 Task Contract 的范围。

1. 读取 Task Contract、PROJECT_START_GATE 引用、相关代码、测试和已有改动；确认 task_id、task_revision、attempt_id、workspace baseline。
2. 以 actual 模式校验 Execution Request 1.3。project_start_gate.status 必须是 APPROVED 或 NOT_REQUIRED；Request 必须包含完整 resolved_execution / resolved_review 和 route_preflight 证据。
3. 不要重新自由选择模型。使用 Request.resolved_execution 指定的 profile/backend/model/effort 启动独立 Worker Session；若真实 route 与 Request 不一致，停止并返回契约错误。
4. Controller 默认不得直接实现当前 Task。只有 Request.governance.controller_worker_override.allowed=true 时才允许 controller_override，并必须使用完全一致的 override reason。
5. 只在 Allowed Paths 内实现，不修改项目级 NEXT/Roadmap。修改后检查真实 diff。
6. 逐个执行 Request.required_checks，以相同 check ID 返回 command/exit code 或 semantic conclusion 与 evidence。
7. Worker Result 必须记录 execution_mode、实际 profile/backend/model/effort、session，以及 invocation.command / exit_code / evidence。没有真实 invocation evidence 不能声明 READY_FOR_REVIEW。
8. 失败记录稳定 failure fingerprint 与 attempt context；第 1 次 retry 保持 Profile，同一 fingerprint 第二次失败后第 2 次 retry 才 escalation。
9. Worker 完成且验证通过时，Execution Result 只能是 READY_FOR_REVIEW；project_integration 保持 NOT_EVALUATED。
10. 返回前运行 execution_contract_validate.py 校验 request/result identity、resolved route、scope、验证证据和状态一致性。