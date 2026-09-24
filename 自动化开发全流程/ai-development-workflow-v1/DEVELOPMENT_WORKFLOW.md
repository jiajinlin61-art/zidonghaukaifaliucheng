# 开发流程概览（首次了解时阅读）

standalone_master 由当前主控管理项目；delegated_worker 仅执行上层交付的一个 Task。项目 Controller 拥有 Roadmap、NEXT、READY/BLOCKED/REVIEW/DONE；执行层只拥有 attempt、路由、失败记录和证据。

生命周期：需求与范围 → 计划确认 → 必要设计/架构 → 任务 → 路由与预检 → 实现 → 验证 → 独立审查 → 集成。

日常执行以 [最小执行规则](PROJECT_EXECUTION_RULES.md) 为入口，详细规则的唯一维护位置见 [上下文索引](policies/CONTEXT_POLICY.md)。本页不重复所有策略。

## 根据规模展开

- FAST：相称的简短计划、一个 Task、合并质量检查；不创建 Phase/Stage 和独立回顾文档。
- STANDARD：简明需求与少量 Task，按实际依赖组织集成。
- FULL：必要的 PRD、原型、架构/API 和阶段计划；计划及设计基线审批均保留。

模式细节由 [DEVELOPMENT_MODES](policies/DEVELOPMENT_MODES.md) 维护，审批触发和例外由 [PROJECT_START_GATE](policies/PROJECT_START_GATE.md) 维护。已有设计制品先核对与复用，仅补缺失或过期部分。

## 完成的层次

命令退出成功不等于业务成功。Task 必须满足验收和独立 Review；多个 Task 完成后，Controller 还需对照完整批准需求并执行真实集成路径。多任务项目可用 PROJECT_ACCEPTANCE 映射要求→任务及要求→集成检查；FAST 直接复用 Task 验收。

Execution Contract 1.4 的 actual CLI 将结构校验与磁盘证据核验串联。纯函数和 template 模式只说明结构；证据记录绑定 task/revision/attempt、工作区和内容，Git 审查同时绑定提交。具体用法按需读 [DELIVERY_EVIDENCE](policies/DELIVERY_EVIDENCE.md)。

本流程止于开发验证、审查和集成。发布/部署另行授权；UADS 后台运行时尚未实现。
