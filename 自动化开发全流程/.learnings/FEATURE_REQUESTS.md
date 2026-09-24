# Feature Requests

Capabilities requested by user that don't currently exist.

---

## [FR-20260922-001] Requirement Conservation & Product Drift Gate

**Logged**: 2026-09-22
**Priority**: critical
**Status**: requested

### Problem
当前流程能保证路由、Task Contract、测试和独立 Review 的局部正确性，但不能充分防止“架构与 PRD 正确，开发任务逐步偏离核心用户工作流”。

### Requested capability
增加跨 Phase/Task 持续生效的 Requirement Conservation & Product Drift Gate，至少包含：
- product_north_star
- primary_user_workflow
- business_invariants
- system_of_engagement
- requirement_traceability
- mock_substitutions
- deferred_must_requirements
- vertical_slice_status
- product_drift_review

### Required behavior
1. Project Start 从原始需求抽取关键业务约束并获得确认。
2. 每个 Execution Request 自动携带相关业务约束和来源引用。
3. Reviewer 不仅审 Task Acceptance，还必须审产品目标漂移。
4. Phase/Project DONE 前检查所有 MUST 需求的真实证据。
5. 技术 Mock Gate 与产品交付 Gate 使用不同状态名称。
6. 核心业务入口被替换、延后或新 UI 抢占主入口时自动进入 NEEDS_HUMAN。
7. 对飞书、Salesforce、ERP 等业务操作中心要求最小 inbound/outbound 垂直切片尽早验证。

### Origin
AI 服装搭配批量生图项目复盘：飞书被 PRD 与 Architecture 定义为业务操作中心，但 Local Mock Core 提前达到 validated，真实 Feishu business sync 尚未形成运行主链路。

---

## [FR-20260922-002] Runtime Route Health & Orphan Session Reconciliation

**Logged**: 2026-09-22
**Priority**: high
**Status**: requested

### Requested capability
在现有 model_router / route_preflight 之上增加运行时健康层：
- live_model_probe
- warning/error taxonomy
- quota detection
- no_progress_watchdog
- orphan_session_reconciliation
- auditable runtime fallback

### Acceptance direction
- unrecognized_model 等非致命 catalog warning 不应覆盖真实 exit=0/有效输出。
- usage limit 能自动标记 backend temporarily unavailable 并选择下一候选。
- Worker 长时间无输出且无目标磁盘变化时可停止并安全 fallback。
- AgentDock 重启后能发现旧 Worker/MCP 子进程，防止重复开发。
- 所有 fallback 进入 Execution Request/Result 审计证据。

### Origin
AI 服装搭配项目 R1 执行：Claude catalog warning、Codex quota exhaustion、长任务无进展、AgentDock 重启后孤儿 Claude 进程同时出现。

---
