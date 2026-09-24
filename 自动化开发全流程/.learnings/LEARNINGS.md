# Learnings

Corrections, insights, and knowledge gaps captured during development.

**Categories**: correction | insight | knowledge_gap | best_practice
**Areas**: frontend | backend | infra | tests | docs | config
**Statuses**: pending | in_progress | resolved | wont_fix | promoted | promoted_to_skill

## Status Definitions

| Status | Meaning |
|--------|---------|
| `pending` | Not yet addressed |
| `in_progress` | Actively being worked on |
| `resolved` | Issue fixed or knowledge integrated |
| `wont_fix` | Decided not to address (reason in Resolution) |
| `promoted` | Elevated to CLAUDE.md, AGENTS.md, or copilot-instructions.md |
| `promoted_to_skill` | Extracted as a reusable skill |

## Skill Extraction Fields

When a learning is promoted to a skill, add these fields:

```markdown
**Status**: promoted_to_skill
**Skill-Path**: skills/skill-name
```

Example:
```markdown
## [LRN-20250115-001] best_practice

**Logged**: 2025-01-15T10:00:00Z
**Priority**: high
**Status**: promoted_to_skill
**Skill-Path**: skills/docker-m1-fixes
**Area**: infra

### Summary
Docker build fails on Apple Silicon due to platform mismatch
...
```

---


## [LRN-20260922-001] insight

**Logged**: 2026-09-22
**Priority**: critical
**Status**: pending
**Area**: docs

### Summary
架构设计正确但实现阶段发生产品目标漂移：局部 Task/Mock Gate 均通过，仍未优先落地 PRD 指定的核心业务操作中心。

### Incident
《AI服装搭配批量生图自动化系统》PRD 明确要求飞书多维表格作为一期核心业务操作界面，运营目标工作方式是“选商品 → 查看候选图 → 最终选图”。Architecture 也正确写明飞书负责业务录入、候选图查看、KEEP/REJECT/REDO 和运营可见状态。

实际实现优先完成了 Local Mock Core：状态机、Provider Port、重试/恢复、ReviewService、模板统计、Outbox、Packaging 较完整，但真实 Feishu Inbound Sync、附件读取/回写、人工审核结果读取、Batch 选品尚未形成可运行垂直链路。同时使用“P0 VALIDATED”描述本地 Mock Core，与 PRD 的一期 P0 必须项产生语义混淆。

### Root causes
1. Task Contract/Reviewer 主要验证局部 Acceptance，未强制回查原始 PRD 的产品级关键约束。
2. 缺少 Requirement Conservation：拆任务后“飞书是业务操作中心”没有作为 Business Invariant 持续注入 Phase/Stage/Task。
3. 水平分层优先于垂直切片：先做 Core/Adapter/Mock Reliability，最重要的真实用户工作流被延后。
4. Mock Gate 未强制登记“替代了什么真实能力、未覆盖什么、何时解除 Mock”。
5. Reviewer 缺少 Product Drift Check：没有强制读取 PRD + Architecture + Requirement Traceability Matrix。
6. 技术阶段 P0 与产品 PRD P0 同名，导致完成语义混淆。
7. UI 原型阶段没有重新检查 Primary User Workflow，容易把独立 Web 后台扩成主业务入口。

### Drift signals that should have triggered a warning
- PRD 明确使用“核心业务操作界面”“不另行强制开发复杂运营后台”。
- Architecture 已明确飞书是运营控制台和录入/复筛入口。
- Feishu client/mapper/outbox 存在，但 list_records、mapped_value、extract_attachment_tokens、upload_bitable_media 没有进入业务主链路。
- Local E2E 能通过，但无法从真实业务入口“选商品”开始，也无法在飞书完成最终复筛。
- PairingService 默认对所有 enabled 商品全组合，而业务意图是“运营选当天商品 → 本批次组合”。
- Web 原型出现“创建批次 / KEEP / REDO / REJECT”作为主要入口时，应触发入口冲突检查。

### Framework improvements to implement
1. Project Start Gate 抽取并确认 Product North Star / Primary User Workflow / Business Invariants。
2. 建立 Requirement Traceability Matrix：PRD Requirement → Phase → Stage → Task → Validation Evidence。
3. 对关键需求标注 MUST_PRESERVE、MUST_DEMONSTRATE_EARLY、CAN_DEFER。
4. 增加 Vertical Slice Gate：跨系统项目在深度内部加固前，先验证最薄真实主链路。
5. 增加 Mock Substitution Ledger，并使用 LOCAL_MOCK_CORE_VALIDATED 等显式状态，禁止与产品级 P0_COMPLETE 混用。
6. Independent Reviewer 强制执行 Product Drift Review，读取 PRD、Architecture、Traceability Matrix 和当前 Phase Objective。
7. 若 PRD 明确外部系统是 system of engagement，其 inbound + outbound 最小链路不得作为普通 Adapter 无限延后。
8. 对“选择一批对象后处理”的业务强制区分全局主数据与本次运行选择集。
9. UI/原型前增加 Prototype Alignment Gate；已有系统若是主操作中心，新 Web UI 默认只能是 Admin/Observability，除非用户批准改变边界。

### Resolution
暂不直接改核心工作流规则。后续升级自动化框架时，将本案例转化为 Project Start Gate、Execution Request、Quality Gates、Reviewer Prompt 和校验工具中的机器可检查字段。

---

## [LRN-20260922-002] insight

**Logged**: 2026-09-22
**Priority**: high
**Status**: pending
**Area**: model-routing / session-runtime

### Summary
静态 Router/Preflight 通过不代表长任务运行时健康；需要区分模型目录警告、真实调用失败、额度耗尽、无进展会话和 AgentDock 重启后的孤儿进程。

### Incident
R1 执行中观察到：
- Claude Code 对 glm-5.3[1M] 输出 unrecognized_model catalog warning，但最小只读调用实际 exit=0 且返回 PROBE_OK，说明该 stderr 不能直接视为调用失败。
- Codex GPT-5.6 Sol 在 Preflight 通过后真实执行时命中 usage limit，静态 probe freshness 无法代表实时额度。
- Claude Code 长任务会话可保持进程存活但约 188 秒无 stdout、无目标文件变化，需要 no-progress 检测。
- AgentDock 重启后 session registry 丢失，但旧 Claude/MCP OS 进程仍可能残留，存在重复 Worker 并发修改风险；本次通过 PID/父子进程树人工识别并清理。

### Framework improvements
1. Runtime probe 必须综合 exit_code + stdout + stderr 分类，warning 不能仅按关键字判失败。
2. 增加 quota/usage-limit 运行时错误分类与即时 fallback，不依赖静态 Preflight。
3. 增加 Worker no-progress watchdog：连续无 stdout/文件变化达到阈值时进入可审计 fallback。
4. AgentDock 恢复后增加 session/process reconciliation，识别并清理 orphan Worker/MCP 子进程。
5. 长任务启动前做轻量 live probe；Preflight 只作为静态环境证据，不再等价于 runtime availability。
6. Execution Result 记录 fallback 原因、实际 backend/session 与被排除 backend，避免路由事实丢失。

---
