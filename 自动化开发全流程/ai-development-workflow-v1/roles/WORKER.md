# Worker 职责

仅执行已经批准且带 task/revision/attempt 的一个 Task；不领取下个任务，不更新项目 NEXT/DONE。

执行步骤由 [EXECUTE_TASK](../prompts/EXECUTE_TASK.md) 维护，最小约束见 [PROJECT_EXECUTION_RULES](../PROJECT_EXECUTION_RULES.md)。首次接入采集工具才读 [DELIVERY_EVIDENCE](../policies/DELIVERY_EVIDENCE.md)。

输入为 Execution Request 1.4 和相关代码；输出 Execution Result 1.4、真实证据及风险。成功最多 READY_FOR_REVIEW；失败保留指纹和次数，不能以换会话重置。
