# 流程库维护入口

本目录是流程规则库及其校验工具，不是业务项目，也没有后台调度器。

- 开始只读本文件、用户当前需求及相关代码；需要了解目录时读 README.md。
- 修改规则：从 ai-development-workflow-v1/policies/CONTEXT_POLICY.md 找到唯一维护位置，仅读对应条目。
- 修改工具：读对应 tools 文件和 tests 测试；不加载所有策略、模板、历史结果。
- 保留用户修改；仅改当前授权范围。用户已确认的计划不重复确认。
- 沿用项目 .venv；命令从本目录运行。先运行 tools/environment_check.py，代码修改后运行 tools/check_tests.py；种子变更才额外运行 tools/bootstrap_validate.py。
- 文档/入口变更运行 tools/workflow_docs_validate.py，检查本地引用和按需入口。
- 流程变更必须核对并同步更新 [新项目接入完整流程使用教程](docs/新项目接入完整流程使用教程.md)，包括受影响的首次接入/恢复提示词、操作步骤、路径、权限、版本和工具使用说明；纯内部改动若不影响使用方式，可不改教程，但交付时说明已核对。教程与当前实现一致是交付检查项，不留到后续补写。
- 完成前核对 diff、实际验证和未验证项。跨窗口更新 docs/OPTIMIZATION_CHECKPOINT.md，恢复时才读取它。
- .uads、SYSTEM_SPEC_V1_REV2.md、IMPLEMENTATION_PLAN.md 属于未来运行时设计，只有明确开发 UADS 才加载。
- 本次优化不开发自动调度、后台唤醒、并行任务执行；不改变模型绑定，不发布或部署。

完整业务执行规则只在业务项目明确启用完整规则包时生效。维护本库不需要为每个编辑任务调用业务项目的 Router/Worker 链路。
