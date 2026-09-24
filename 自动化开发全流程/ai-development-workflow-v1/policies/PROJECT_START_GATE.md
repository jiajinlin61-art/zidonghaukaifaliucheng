# Project Start / Plan Approval Gate

新项目不能把“用户授权开发”自动解释为“可以跳过方案确认并直接编码”。对复杂、跨系统或高风险项目，开发计划确认是独立的硬 Gate。

## 何时必须确认计划

满足以下任一条件时，`plan_gate.required=true`：

- mode = FULL；
- complexity = COMPLEX / CRITICAL；
- risk = HIGH / CRITICAL；
- cross_system = true；
- architecture_change = true；
- 用户明确要求先确认方案或开发计划；
- 新功能或实质性范围变化（explicit_plan_approval_required=true）。

FAST/TRIVIAL/SIMPLE 且低风险、单系统、无架构变更时，仅在不涉及新功能或实质性范围变化时才可标记 NOT_REQUIRED。每个新功能需求或实质性范围变化都设置 explicit_plan_approval_required=true，使机器门禁也要求用户确认；一旦标记 required，就不能静默取消。

## Gate schema 1.1 与 FULL 的第二次审批

gate 文件使用 `templates/PROJECT_START_GATE.yaml`（schema 1.1）：

- **FAST/STANDARD**：只有一次按任务规模缩短的计划审批（`plan_gate`）。schema 1.0 的 FAST/STANDARD gate 文件行为保持不变。
- **FULL**：需要两次硬审批：
  1. `plan_gate`：详细设计前，用户确认范围、初始技术选型（如适用）和总体计划；
  2. `design_gate`：任何功能代码前，用户确认设计基线。

`design_gate.artifacts` 覆盖六项制品：technical_selection、prd、prototype、architecture、api_contract、implementation_plan。每项 `status` 为 `ready` 或 `not_applicable`；`not_applicable` 必须附非空 `reason`。机器规则：

- prd / architecture / implementation_plan 在 FULL 中必须 ready；
- technical_selection 在新项目中必须 ready，现有项目可 N/A（复用现有栈，需理由）；
- has_ui=true 时 prototype 必须 ready；前后端项目的 api_contract 必须 ready；不适用的制品必须 N/A 且附理由；
- `design_gate.user_approved=false` 时 Implementation 必须 BLOCKED。

**Legacy 迁移**：schema 1.0 的 FULL gate 文件在校验时 fail closed，必须迁移到 1.1（补充 `has_ui` 与 `design_gate`）后才能放行实现。

## Gate 前必须完成

- requirements_read = true：已完整读取用户提供的需求/Brief；
- architecture_ready = true：需要架构设计时已形成架构方案；不需要时说明 N/A；
- development_plan_ready = true：已形成可审阅的开发计划，至少包含范围、阶段/任务、风险、验收和模型执行分工；
- 将方案呈现给用户；
- user_approved = true，并记录 approval_ref（FULL 的两次审批各自记录 approval_ref）。

`user_approved=false` 时，Implementation 必须保持 BLOCKED。允许继续做读取、分析、计划、无副作用的环境检查和文档整理，但不得进入业务代码实现。

小任务计划可以只有目标、范围、相关组件、验收和风险。已批准范围内的后续 Task、修复和补测连续推进，不重复索要批准；目标或范围改变时才提交修订计划。

## 与一般授权的关系

本 Gate 是显式人工检查点，优先于“可逆项目内编辑可自动继续”的一般授权规则。用户先前说“自动完成项目”并不等价于批准尚未展示的复杂开发计划。

## 机器校验

使用：

```powershell
.\.venv\Scripts\python.exe tools/project_start_gate_validate.py --gate <PROJECT_START_GATE.yaml> --require-implementation
```

当 Gate 未批准、状态不一致、Implementation 不允许、FULL 缺少 design_gate / 审批 / 必需制品，或制品 N/A 无理由时，命令必须非零退出。
