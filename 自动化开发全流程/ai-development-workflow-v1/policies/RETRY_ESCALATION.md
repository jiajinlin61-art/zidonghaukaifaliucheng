# Retry & Escalation

失败分类：环境/依赖、输入或需求不清、实现缺陷、测试缺陷、架构缺陷、权限/外部系统。

## 1. Attempt 与 Retry

- 第 1 次执行是 initial attempt，不计入 retry。
- 默认 `max_retries: 2`，因此同一 Task Revision 最多 3 次 attempt：首次执行 + 2 次重试。
- 每次 attempt 必须有新的 `attempt_id`，失败记录不得被后一次覆盖。
- 换 Session、换模型、换 Executor 不会重置已经发生的同类失败次数。

## 2. Failure fingerprint

fingerprint 表示“根因签名”，用于跨 attempt 识别同一类失败。建议输入：

```text
task_id + task_revision + error_code
+ normalized exception/message
+ failing command / verifier
+ stable failing path or interface
```

attempt context 另行记录 model、backend、session、commit、diff/artifact hash、时间和原始日志。它们用于复现，但不进入 fingerprint；因此仅仅换模型或换 Session 不会把同一失败伪装成新失败。

如果 error code、失败接口/路径或归一化根因实质变化，可以生成新的 fingerprint。

## 3. 默认升级顺序

- initial attempt 失败：记录 fingerprint 和证据。
- 第 1 次 retry：同一 Profile 内基于新证据修复。
- 同一 fingerprint 再次失败后，第 2 次 retry：按 Model Routing escalation 升一级 Profile。
- 仍失败：预算耗尽，进入 NEEDS_HUMAN；不得继续无限换模型。

环境/依赖问题先修环境。输入或需求歧义直接进入 NEEDS_HUMAN。权限、凭据、数据损失风险、不可逆操作或范围争议立即停止相关范围。

## 4. Budget 语义

`max_retries` 表示 initial attempt 之后允许的额外重试次数，不表示总 attempt 数。

Task、Stage、Run 如各自存在预算，最窄范围先耗尽时立即停止该范围并记录预算报告。预算耗尽统一进入 NEEDS_HUMAN，由人决定修改定义、改变路由、扩大预算或结束任务。

任何重试都必须记录：

- attempt_id
- failure fingerprint
- attempt context
- route/profile/backend/model
- 实际验证
- retry reason

禁止通过新 Session、新模型或新 attempt ID 清零失败计数。
