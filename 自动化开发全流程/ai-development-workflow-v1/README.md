# 完整规则包入口

这是可选的完整规则包；starter 仍可独立使用。模型绑定与路由策略不因本次优化改变。

日常只读 [最小执行规则](PROJECT_EXECUTION_RULES.md) 和当前 Task；发生具体决策时查 [按需索引](policies/CONTEXT_POLICY.md)。不要逐个打开本目录的所有文件。

- 首次了解全流程才读 [流程概览](DEVELOPMENT_WORKFLOW.md)。
- 新功能审批或范围变化才读 [开发审批](policies/PROJECT_START_GATE.md)。
- Worker/Reviewer 首次接入证据工具才读 [证据操作](policies/DELIVERY_EVIDENCE.md)。
- 跨任务规划与最终集成才用 [项目验收映射](templates/PROJECT_ACCEPTANCE.yaml)。

Execution Contract 1.4 的实际成功门禁检查磁盘证据；1.3 历史记录不能直接当成 1.4 已验证结果。只有模板结构检查不读取执行产物，也不代表执行成功。

本包不提供后台调度器，不自动领取下一项任务。项目状态由当前 Controller 管理。
