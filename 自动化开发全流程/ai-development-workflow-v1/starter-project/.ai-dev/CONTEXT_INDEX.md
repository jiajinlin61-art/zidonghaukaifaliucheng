# 项目按需读取索引

本文件无需每轮读取；已知道下一步所需文件时直接读取相关部分。

| 触发 | 加载 |
|---|---|
| 首次接入/共享版本或权限变化 | 项目 AGENTS.md 接入记录；共享包 policies/SHARED_LIBRARY_USAGE.md 的相关段落 |
| 新任务 | AGENTS.md、当前需求/Task、相关源码/测试 |
| 新功能审批或范围变化 | .ai-dev/PROJECT_START_GATE.yaml、对应计划段落 |
| 不清楚当前进度 | .ai-dev/CURRENT_STATE.md |
| 中断/换窗口恢复 | CURRENT_STATE.md + CHECKPOINT.md；核对真实工作区和最小验证 |
| 需求语义有疑问 | docs/PROJECT_BRIEF.md / PRD.md 中相关章节 |
| 改动触及模块接口/基础设施 | docs/ARCHITECTURE.md 中有关边界/API |
| 选择下一项任务/集成 | docs/IMPLEMENTATION_PLAN.md 当前任务与依赖；集成时核对全部批准需求 |
| 审查或失败调查 | 当前 diff、命令摘要、必要日志片段 |

以上路径相对项目根。缺失文件先判断是否适用；不为了满足目录形状创建空文档。状态文件、计划和 checkpoint 各有职责，不维护重复任务清单。

同一会话未改变的规则不反复读。禁止默认递归加载全部 Markdown、其它任务日志或完整外部规则包。完整包仅在项目明确启用时，从其 CONTEXT_POLICY 按阶段查询。
