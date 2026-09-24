使用独立 Reviewer 会话审查当前 Task；只读 Request、Result、实际 diff 和必要验证摘要，不读取全项目历史。

先运行 actual 契约与磁盘证据门禁，要求 Worker 为 READY_FOR_REVIEW。模型 Reviewer 必须与 resolved_review 一致且不同于 Worker 会话；用 delivery_evidence.py 包装审查命令（kind=review），保持交付文件不变。人工审查保存真实报告及 reviewer_id，不伪造进程记录。

核对目标、允许路径、错误处理、兼容性和真实用户行为。需要时独立复验相关检查。每次审查绑定 task/attempt、delivery.content_sha256 和 Git 完整提交号；审查后交付发生变化则重新审查。

把 reviewed_content_sha256、reviewed_commit 和 invocation.receipt 写入 review；真实退出成功且结论 PASS 才返回 REVIEW_PASSED。FAIL 返回修复证据，需用户决定则 NEEDS_HUMAN。review_revision 表示审查轮次，不是 task_revision 的替代物。

再次运行 execution_contract_validate.py --request REQUEST --result RESULT --evidence-root EVIDENCE_DIR。project_integration 保持 NOT_EVALUATED；Reviewer 不声明项目 DONE。详细字段仅首次接入时读 policies/DELIVERY_EVIDENCE.md。
