# 按需读取索引

本文件是读取规则的唯一维护位置；它是索引，不是“全部必读”清单。

## 最小上下文

- 新任务：项目 AGENTS + 当前需求/Task + 直接相关源码和测试。完整包的最小执行规则同一会话读一次即可。
- CURRENT_STATE：已有长任务或需要确定当前位置时读取；CHECKPOINT：中断恢复或换窗口才读取。
- 从目录/搜索定位相关段落，再读取正文；同一会话未改变的文件不重复读取。文件已变更、发现冲突或关键验收时重新核对有关部分。
- 已批准的 PRD/原型/架构不重建，只读当前需求对应章节与依赖约束。
- 不运行“读取全部 md/整个 policies/templates”的批量加载；不默认读取 UADS 规格、.uads、.learnings、全部历史结果或其它 Task 日志。
- 不用任意 token 截断丢弃验收/禁止事项；摘要保留目标、边界、未决问题、证据引用和下一动作，详细证据留在磁盘。

## 触发后只选对应行

| 当前问题/阶段 | 读取位置（相对规则包） | 何时停止加载 |
|---|---|---|
| 首次接入/共享路径、权限或版本变化 | policies/SHARED_LIBRARY_USAGE.md + 项目接入记录 | 核实路径、版本、权限及输出归属 |
| 不清楚工作规模 | policies/DEVELOPMENT_MODES.md；需要量化时再读 PROJECT_COMPLEXITY.md | 确定模式 |
| 新功能、范围变化、FULL 设计审批 | policies/PROJECT_START_GATE.md + 项目当前 gate | 确定批准范围/缺失项 |
| 首次组织任务或跨任务交付 | 当前计划对应任务；templates/EXECUTION_REQUEST.yaml | 当前任务契约完备 |
| 模型路由/能力不满足 | policies/MODEL_ROUTING.md；实际运行 tools，读取摘要 | 得到 resolved route 和 preflight |
| 启动 Worker | prompts/EXECUTE_TASK.md；首次采集才读 DELIVERY_EVIDENCE.md | 明确当前任务及返回约定 |
| 独立审查 | prompts/REVIEW_TASK.md + 当前 diff/验证摘要 | 当前审查完成 |
| 测试/进程失败 | policies/RETRY_ESCALATION.md；需要根因定位才读 roles/DEBUGGER.md | 下一次动作有新证据 |
| 中断恢复 | policies/CHECKPOINT_RECOVERY.md + 当前 checkpoint | 当前工作区及下一步已核实 |
| 集成/阶段验收 | policies/QUALITY_GATES.md；多任务才用 PROJECT_ACCEPTANCE.yaml | 当前集成验收完成 |
| Git 隔离/合并问题 | policies/GIT_WORKFLOW.md | 解决当前 Git 决策 |
| 授权边界不明确 | policies/HUMAN_APPROVAL.md + 当前批准记录 | 明确可执行范围 |

路径简写在 policies/ 下解析；tools 在规则库根目录，模板在 templates/。角色职责不明确时才读对应 roles 文件，不把 role 与 prompt 全套重复加载。

## 证据与交接

先读退出码、摘要和失败位置；仅失败调查或审查需要时打开原日志相关片段。Request/Result 只保留必要字段与引用；工具自动填入命令、退出码、改动路径和摘要，不让模型抄写整段日志。跨会话交接用已有 checkpoint，不另建第二套计划。
