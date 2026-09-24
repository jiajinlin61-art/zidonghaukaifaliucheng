# Delegate READY Task to Execution Workflow

把占位符替换成真实路径和 Task ID。

```text
继续 <TARGET_PROJECT_PATH> 的 <TASK_ID>。

Project Controller 仍由 GPT-TaskBoard 负责；下游执行工作流只完成当前 Task Revision，不得自行领取下一项目级 Task，也不得更新项目级 NEXT/DONE。

先读取目标项目：
- Agent 入口
- status / roadmap / task-board
- 当前 Task 的 development plan / spec / ADR
- git status / worktree / main HEAD
- 当前 Claim ID / Owner / Task Revision

确认当前 Claim 仍有效，并读取：
- task_id / task_revision
- objective
- dependencies / gate
- Complexity / Risk / Task Kind
- Allowed Paths / forbidden/shared paths
- Acceptance（稳定 ID）/ required validation checks（稳定 ID、kind、acceptance_ids）
- stop conditions
- repository baseline

然后读取 <AI_DEVELOPMENT_WORKFLOW_PATH>：
- DEVELOPMENT_WORKFLOW.md
- policies/MODEL_ROUTING.md
- policies/RETRY_ESCALATION.md
- routing/MODEL_BINDINGS.yaml
- roles/WORKER.md
- roles/DEBUGGER.md
- roles/REVIEWER.md
- templates/EXECUTION_REQUEST.yaml
- templates/EXECUTION_RESULT.yaml
- tools/execution_contract_validate.py
- tools/route_preflight.py

把当前 Task Revision 转成 Execution Request 1.2：
- 分配唯一 attempt_id；
- 默认 max_retries=2（首次执行 + 最多 2 次 retry）；
- 写入 workspace root / repository baseline；
- 把每个 Acceptance 分配稳定 ID，并让 validation.required_checks 用 acceptance_ids 完整覆盖；
- 明确 allowed_paths / forbidden_paths；
- Profile 默认为 auto；override 必须有原因且不能降低最低能力；
- 写清 stop_conditions。

执行前先以 `--mode actual` 运行 execution_contract_validate.py 校验 Request，再运行 route_preflight.py；任一失败都不得进入 Worker。原始模板只能用 `--mode template` 做结构检查，不能当实际成功结果。

规则：
1. Worker 使用独立 Session 完成实现与测试。
2. failure fingerprint 表示稳定根因；model/backend/session/commit 属于 attempt context，不能用来重置同类失败次数。
3. 首次失败记录 fingerprint；第 1 次 retry 保持当前 Profile；同一 fingerprint 再次失败后，第 2 次 retry 才允许 escalation。
4. Worker 成功且验证通过只返回 status=READY_FOR_REVIEW / review=PENDING；changed_paths 必须全部在 allowed_paths 且不得命中 forbidden_paths，每个 required check ID 都必须有对应结果。
5. 独立 Reviewer PASS 后才更新为 status=REVIEW_PASSED / review=PASS。模型 Reviewer 必须使用与 Worker 不同的 session，并记录 review_revision/independence_evidence；人工 Reviewer 必须记录 reviewer_id 和证据。
6. Execution Result 的 project_integration.status 始终保持 NOT_EVALUATED。
7. 返回前以 actual 模式同时校验 Request + Result，拒绝占位符、task/revision/attempt/baseline 不一致、验证覆盖缺失、未授权 check、越权/禁止路径、Reviewer 非独立、失败 fingerprint 为空或状态矛盾。
8. Project Controller 根据真实 commit、diff、测试、Review 和 main Gate 决定 REVIEW/DONE/BLOCKED。

最终返回：
- Task ID / Revision / Attempt ID
- Worker route
- branch / commit / changed paths
- validation command / exit code / evidence
- Reviewer route 与 evidence
- failure fingerprint / same-fingerprint count（如有）
- remaining risks
- 建议的 TaskBoard 状态变化（仅建议，不直接改 NEXT/DONE）
```
