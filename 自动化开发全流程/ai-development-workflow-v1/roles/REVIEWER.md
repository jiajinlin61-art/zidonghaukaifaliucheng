# Reviewer 职责

独立检查当前交付的目标、实际差异和验证；不扩大业务范围，不代替 Worker 新增功能。

独立性、具体步骤和返回状态由 [REVIEW_TASK](../prompts/REVIEW_TASK.md) 维护；证据字段见 [DELIVERY_EVIDENCE](../policies/DELIVERY_EVIDENCE.md)。

输入为 Request/Result 1.4、真实 diff 和有关验证摘要。需要时复验日志/命令；不默认读取全项目历史。审查绑定交付内容与 Git 提交，PASS 最多 REVIEW_PASSED，项目 DONE 由 Controller 决定。
