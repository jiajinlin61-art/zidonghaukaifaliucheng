以独立 Reviewer Session 审查当前 Task。

读取 Execution Request 1.3、Worker Execution Result、真实 diff、task revision / attempt identity 和验证输出。先确认 Worker Result 为 READY_FOR_REVIEW 且契约校验通过。

必须使用 Request.resolved_review 指定的 profile/backend/model/effort，不得自行降级或复用 Worker Session。模型 Reviewer 的 session 必须与 Worker session 不同；Reviewer invocation 必须记录 command、exit_code 和 evidence。人工 Reviewer 则记录稳定 reviewer_id 和独立审查证据。

检查真实 diff 是否与 Worker changed_paths 一致、是否全部在 Request scope 内、每个 required check 是否有对应证据，以及 Acceptance、错误处理、兼容性、数据安全、幂等性和回归风险。不得只相信 Worker 的文本结论；必要命令应独立复验。

输出后更新 Execution Result：
- PASS → status=REVIEW_PASSED，review.status=PASS；
- FAIL → status=FAILED，review.status=FAIL，并附 required fixes；
- 需要人工判断 → status=NEEDS_HUMAN。

project_integration.status 保持 NOT_EVALUATED。Reviewer 不声明项目级 DONE，也不实现新的业务范围。返回前再次运行 execution_contract_validate.py，确保 Reviewer route 与 resolved_review 一致且独立性证据有效。