# 质量门禁（验收时读取）

计划/设计审批以 PROJECT_START_GATE.md 为唯一详细来源；模式以 DEVELOPMENT_MODES.md 为准。已有授权不重复请求。

- Route：实际解析和预检通过，Worker/模型 Reviewer 与已解析路线一致。
- Task：可观察目标满足、相关验证通过、真实差异在 scope 内；成功进程与证据一致。
- Independent Review：不同会话或人工，核对真实交付。审查绑定具体内容及 Git 提交，改变交付后审查失效。
- Integration：Controller 核对整合后的目标基线，运行必要集成/端到端检查，确认批准需求没有在任务拆分中丢失。
- Stage/Phase：仅在项目实际存在这些层级时执行，核对该阶段目标、集成路径、风险和状态。

完整包实际成功门禁必须使用 Contract 1.4 actual CLI，具体操作按需读 DELIVERY_EVIDENCE.md；template 或纯结构检查不等于交付通过。

多任务项目在规划时建立 requirements→tasks/checks 映射，在集成时用 project_acceptance_validate.py 检查覆盖及当前版本的真实检查证据。FAST 复用 Task 验收，不重复创建项目验收表。映射通过不证明任务完成，Controller 仍须核对每个 Task 的独立 Review。

测试按风险和变更范围运行。修复后复验失败项及受影响路径，集成时再做全量/端到端；没有新变化或未解决问题时不反复跑全套。UI 使用真实用户路径，模拟检查不能证明外部系统接通。

任一门禁失败不得推进依赖工作；执行层最多返回 REVIEW_PASSED，项目 DONE 由 Controller 决定。流程止于开发验证与集成，不自动部署。
