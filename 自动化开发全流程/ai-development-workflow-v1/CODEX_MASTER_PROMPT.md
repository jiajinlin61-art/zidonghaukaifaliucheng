# 主控启动入口

先读 PROJECT_EXECUTION_RULES.md、项目当前需求/Task 和相关代码；不要加载本包全部文件。需要补充规则时查 policies/CONTEXT_POLICY.md，只读命中的条目。

确定 standalone_master 或 delegated_worker。已有批准范围连续推进；新功能/范围变化按计划审批规则执行，FULL 保留设计基线审批。复用已存在的需求、原型和架构。

当前 Task 按 prompts/EXECUTE_TASK.md 执行，独立审查按 prompts/REVIEW_TASK.md。完整包使用 Contract 1.4 的 actual 证据门禁。Controller 最终核对项目需求覆盖和集成，执行层不声明项目 DONE。

中断才读 checkpoint/恢复策略；失败才读重试/Debug 策略。只报告当前进展、关键证据和下一动作。
