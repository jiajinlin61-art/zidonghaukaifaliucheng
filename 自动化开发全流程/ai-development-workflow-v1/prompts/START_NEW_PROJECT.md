读取本项目 AGENTS、Brief/需求文档、CURRENT_STATE、PROJECT_START_GATE，以及现有代码、Git/文件基线和已有修改。

先完成 Project Intake、复杂度/风险判断和 FAST/STANDARD/FULL 模式选择，再生成该模式需要的最小文档。FAST 保持最小闭环；STANDARD 默认使用简明 Scope/Spec + Task Contract + Verify + Independent Review；FULL 使用完整需求/架构/开发计划，并按真实需要展开 Phase → Stage → Task。

对新项目，先计算 Project Start / Plan Approval Gate。只要满足 FULL、COMPLEX/CRITICAL、HIGH/CRITICAL risk、跨系统、架构变更，或用户明确要求先确认方案中的任一条件：
1. 完整读取需求；
2. 形成架构方案；
3. 形成可审阅的开发计划，至少包含范围、阶段/任务、风险、验收和模型执行分工；
4. 把计划呈现给用户；
5. 在用户明确确认前，将 implementation.allowed 保持为 false。

Gate 未通过时，只允许继续分析、计划、只读检查和文档整理；禁止进入业务代码 Implementation。用户先前授权“自动开发”不等价于批准尚未展示的复杂开发计划。

计划 Gate 通过后，为每个执行 Task 生成 Execution Request 1.3。必须实际运行 Model Router 和 route_preflight，把 resolved_execution / resolved_review、preflight command、exit code、evidence 写入 Request。Controller 默认不得直接实现 routed Worker task；只有 Execution Request 明确授权 controller_worker_override 且记录原因时才允许。

Worker 必须使用 resolved route 对应的 backend/model/profile，并记录独立 session 与真实 invocation evidence。Worker 完成后进入独立 Review；Reviewer 必须使用独立 Session，且与 resolved_review 一致。Gate 通过后才能进入项目集成或下一 Task。

在已有授权范围内连续推进；尚未授权的破坏性、外部、付费、权限/凭据变更和业务取舍仍按 HUMAN_APPROVAL 规则处理。

Apply plan approval to every new functional request: show a concise or full plan according to task complexity, set explicit_plan_approval_required=true, and wait for explicit approval before implementation, even when FAST is selected. Approval authorizes only the stated scope; re-plan and obtain approval if the goal or scope changes.
