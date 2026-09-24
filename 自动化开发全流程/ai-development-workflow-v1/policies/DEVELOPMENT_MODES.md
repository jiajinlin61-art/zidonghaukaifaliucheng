# Development Modes

FAST、STANDARD、FULL 是**同一个工作流的三种配置**，不是三个工作流。三者复用同一执行核心：Task Contract、route + route preflight、验证、独立 Review、retry/recovery、goal alignment 和 handoff。模式只改变设计制品的深度和人工审批的次数，不改变任何安全、验证和 Review 规则。

## 模式矩阵

| Mode | 计划/设计制品 | 人工审批 | 任务结构 |
|---|---|---|---|
| FAST | 简短计划（目标/范围/验收，数行即可） | 一次简短计划审批（`explicit_plan_approval_required=true`） | 单个 Task |
| STANDARD | Mini Spec + 必要的架构/API 增量说明；仅当存在实质性 UI/流程不确定性时才做原型 | 一次按任务规模缩短的计划审批 | 少量 Task；出现多组依赖/跨模块集成/长周期交付时才展开 Phase/Stage |
| FULL | 技术选型（仅新项目或重大技术变更）+ PRD + 原型（有 UI 时）+ 架构与 API 契约 + 分阶段任务计划 | 两次硬审批（见下） | Phase → Stage → Task |

## FULL 的两次硬审批

1. **计划审批（plan_gate）**：详细设计开始前，用户确认范围、初始技术选型（如适用）和总体计划（阶段、风险、验收、模型分工）。
2. **设计基线审批（design_gate）**：任何功能代码开始前，用户确认 PRD/原型/架构基线（含 API 契约与分阶段任务计划）。

STANDARD 和 FAST 只使用一次适当缩短的计划审批。机器校验见 `PROJECT_START_GATE.md` 与 `tools/project_start_gate_validate.py`（gate schema 1.1）。

## 制品适用性规则

- 现有项目通常复用其技术栈；technical_selection 仅在新项目或重大技术变更时要求，否则在 gate 中标记 `not_applicable` 并写明理由。
- 有 UI 的项目需要原型（PROTOTYPE.md），无 UI 项目标记 `not_applicable` 并写明理由；只有包含后端代码的前后端项目才要求 API 契约 ready。静态 UI 或纯后端项目将不适用制品标为 `not_applicable` 并说明理由。
- 任何 `not_applicable` 的设计制品都必须给出非空理由；validator 会拒绝缺失或无理由的 N/A。
- 模板见 `templates/TECHNICAL_SELECTION.md`、`templates/PROTOTYPE.md`、`templates/PRD.md`、`templates/ARCHITECTURE.md`、`templates/IMPLEMENTATION_PLAN.md`、`templates/MINI_SPEC.md`。

## 前后端项目实施顺序

有 UI 且含服务端代码的项目：使用 `frontend/` 与 `backend/` 分离目录；先定义 API 契约；仅新项目或确有需要时搭建新基架；前端从原型实现；后端按 PRD 与 API 契约实现。

## 升降级

可因证据升级：范围扩大、失败重复、风险上升则 STANDARD→FULL；低风险且边界收窄可降级，但必须记录理由。

## 边界

本流程止于开发验证、独立 Review 与集成；不包含部署或生产验收。测试成本与任务成比例（见 `DEVELOPMENT_WORKFLOW.md` 的 Execution clarifications）。
