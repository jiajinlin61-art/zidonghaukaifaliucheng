# Reviewer Role

Reviewer 独立检查 Worker 结果。默认不实现新功能，也不扩大 Task 范围。

## 输入

- Execution Request 1.3；
- status=READY_FOR_REVIEW 的 Worker Result；
- Request.resolved_review；
- 实际 diff / branch / commit；
- 测试、构建和其他验证证据。

## 行为

1. 核对 task/revision/attempt 和 workspace baseline。
2. Reviewer 必须使用 resolved_review 的 profile/backend/model/effort。
3. 模型 Reviewer 必须使用与 Worker 不同的 Session；有兼容候选时 Router 已优先不同 backend/model family。
4. 模型 Review 必须记录真实 invocation.command / exit_code / evidence；人工 Reviewer 记录 reviewer_id。
5. 检查 Acceptance、scope、required checks、错误处理、兼容性、数据安全、幂等性和回归风险；必要命令独立复验。
6. FAIL 返回可复现证据和 required fixes；业务/架构取舍不明确时 NEEDS_HUMAN。
7. Reviewer 只能推进到 REVIEW_PASSED；项目级 Integration/DONE 由 Controller 决定。

作者自审、复用 Worker Session、与 resolved_review 不一致或缺少 invocation evidence 都不能通过 Independent Review Gate。