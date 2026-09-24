# 项目使用入口

本目录可独立于原工作流包使用，规则在 `AGENTS.md`，进度在 `.ai-dev/`。只复制本目录时使用轻量流程；完整规则包的 Model Router、route_preflight 和 Execution Contract 工具并未包含在本目录中，不能声称已经运行这些机器门禁。

## 开始

1. 在 `docs/PROJECT_BRIEF.md` 写明目标、范围内/范围外、约束和成功标准。也可以先告诉助手需求，让它整理到 Brief。
2. 让 AI 开发助手在本项目目录工作，发送下面的请求：

> 阅读本项目 AGENTS.md、docs/PROJECT_BRIEF.md、.ai-dev/PROJECT_START_GATE.yaml 和 .ai-dev/CURRENT_STATE.md，核对现有代码与环境。我授权你按 Brief 完成范围内的开发、测试、修复和交付。先判断复杂度/风险和模式；需要计划确认时先展示计划，得到明确确认后再进入业务代码。在只复制 starter 的轻量流程中，按任务选择实际可用的执行者，完成验证和独立 Review，并如实记录证据；只有明确启用完整规则包且工具可用时，才执行其中的 Model Router、route_preflight 和 Execution Contract 机器门禁。关键进展及中断前更新状态和 checkpoint。最终提供可运行结果、启动方法、实际验证/Review 证据和剩余限制。

## 恢复

在本项目目录发送：

> 阅读 AGENTS.md、.ai-dev/PROJECT_START_GATE.yaml、.ai-dev/CURRENT_STATE.md、.ai-dev/CHECKPOINT.md 和当前计划，对照工作区核实进度。恢复时不得把 PENDING 的计划确认 Gate 当作已批准，也不得跳过既有 resolved route / Review Gate；保留人工阻塞和失败计数，从已核实的未完成处继续。

这套文件由开发助手读取执行，本身不会后台运行。轻量流程无需安装 UADS 或原工作流包；项目自身需要的依赖与启动方法由实施过程确定并记录。若项目选择完整规则包，需在项目规则中明确其位置和版本，并确认所需工具、模型配置和 CLI 实际可用。


每个新的功能需求（包括 FAST 小任务）都先形成与任务规模相称的计划并等待用户明确确认，再进入功能实现。FAST 计划可直接写在对话中；一个任务只保留必要的范围、验收和验证证据，不必创建 Phase/Stage 文档或复制完整日志。已批准范围内的修复和补测继续推进，不重复请求确认；范围或目标改变时重新计划并确认。
