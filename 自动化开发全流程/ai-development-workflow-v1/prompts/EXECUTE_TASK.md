只执行当前 Task Contract。日常只读本提示、当前契约及相关实现；首次使用证据工具时读 policies/DELIVERY_EVIDENCE.md。

1. 核对 task/revision/attempt、批准范围、基线、现有改动；用 actual 校验 Request 1.4。resolved routes 和预检必须有效。
2. 使用 resolved_execution 的实际执行者启动独立 Worker；Controller override 必须由 Request 明确允许。不自行换模型或扩大任务。
3. 用 delivery_evidence.py 包装真实 Worker 命令，证据存工作区外；工具记录任务前后内容。保持唯一 receipt 名称，失败修复使用新 attempt 或新记录，不覆盖旧证据。
4. 用同一工具执行每个 required command check（kind=check:ID）。校验命令不得改变交付源码；语义检查保存具体报告和内容摘要。按命令摘要自动填 Result，不复制日志。
5. Worker 成功且验证通过才返回 READY_FOR_REVIEW；声明的 changed_paths 必须与采集差异完全一致，审查/验证绑定 delivery.content_sha256。
6. 返回前运行 execution_contract_validate.py --request REQUEST --result RESULT --evidence-root EVIDENCE_DIR。actual 是默认模式；template 不能用来批准实际结果。
7. 失败才读取重试策略，保留指纹/计数；不更新项目 NEXT/DONE。集成由 Controller 完成。
