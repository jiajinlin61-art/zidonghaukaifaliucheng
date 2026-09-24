# 自动化开发工作流

当前可用：由 AI 助手执行的需求、计划、开发、验证、独立审查和集成流程，以及本地校验工具。UADS 后台自动执行器尚未实现；本轮不建设调度器。

## 日常从哪里开始

- 新业务项目：复制 [starter-project](ai-development-workflow-v1/starter-project/README.md)，包含隐藏的 `.ai-dev`。已有项目只合并缺失内容，不覆盖规则或现有修改。
- 首次接入和多项目共用：按 [使用教程](docs/新项目接入完整流程使用教程.md) 核对预置路径、版本、只读权限及项目专属证据目录。
- 维护本流程库：只读 [AGENTS.md](AGENTS.md) 和当前相关实现。
- 明确启用完整规则包：先读 [最小执行规则](ai-development-workflow-v1/PROJECT_EXECUTION_RULES.md)，遇到具体步骤再查 [按需读取索引](ai-development-workflow-v1/policies/CONTEXT_POLICY.md)。

不要把目录中的全部 Markdown、模板、日志或 UADS 规格一次性加载到上下文。文件多不代表每次都要读。

## 启动业务任务

> 读取本项目 AGENTS.md、当前需求与相关代码。按需读取当前状态；新功能先展示与规模相称的计划并取得确认，已有批准范围连续推进。只加载当前步骤必要的规则和模板，保留已有修改。完成开发、验证、独立审查和集成，报告真实证据及未验证事项。

恢复时：

> 读取本项目 AGENTS.md、CURRENT_STATE 和 CHECKPOINT，核对当前文件与 Git、未决人工请求和失败计数。按 checkpoint 的下一步继续原授权范围；仅补读该步骤需要的文件。

## 轻量与完整规则包

starter 可独立使用，不带完整路由和校验工具。只有项目明确启用完整规则包，才要求完整 Router、Preflight、Execution Contract 1.4 与磁盘证据门禁。不要声称调用了未提供的工具。

完整规则包的证据采集由 [delivery_evidence.py](tools/delivery_evidence.py) 执行，自动输出命令、退出码、日志引用、内容摘要和实际改动文件；模型只引用摘要，不复制全部日志。详细命令仅在首次采集/审查时读 [证据操作说明](ai-development-workflow-v1/policies/DELIVERY_EVIDENCE.md)。

## 环境与检查

从本目录、使用现有 `.venv` 运行：

```powershell
& '.\.venv\Scripts\python.exe' -B tools/environment_check.py
& '.\.venv\Scripts\python.exe' -B tools/check_tests.py
& '.\.venv\Scripts\python.exe' -B tools/workflow_docs_validate.py
```

目录移动后环境检查会指出旧安装路径；环境修复步骤见 [开发说明](docs/DEVELOPMENT.md)。项目验收不能以模板检查、零测试或单元测试通过代替真实用户路径验证。

## 非日常材料

[src/uads](src/uads/__main__.py) 目前只输出版本；`.uads`、UADS 规格和根目录实施计划仅用于未来运行时开发。不要复制到业务项目。此目录属于父级 Git 仓库，实际仓库根以 Git 检查为准。

本轮改动及验证记录见 [优化检查点](docs/OPTIMIZATION_CHECKPOINT.md)，仅维护/恢复时读取。
