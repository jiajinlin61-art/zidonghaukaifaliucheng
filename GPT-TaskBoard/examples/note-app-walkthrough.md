# 示例：笔记应用从 READY 到 DONE

这是一个虚构案例，用来演示完整状态变化。它不是需要复制的产品架构。

## 1. 当前项目状态

```text
阶段：N1 Local Notes
当前 NEXT：N1-02 File Repository
测试基线：contract tests PASS
```

Task Board：

| ID | Rev | Task | Status | Owner | Depends On | Complexity | Risk | Allowed Paths | Acceptance |
|---|---:|---|---|---|---|---|---|---|---|
| N1-01 | 1 | Note / Notebook contracts | DONE | agent-a | — | STANDARD | MEDIUM | `src/domain/**`, tests | contract tests PASS |
| N1-02 | 1 | File repository | READY | — | N1-01 | STANDARD | MEDIUM | `src/storage/**`, `tests/storage/**` | create/read/update/reopen PASS；损坏文件返回明确错误 |
| N1-03 | 1 | CLI integration | BACKLOG | — | N1-02 | SIMPLE | LOW | `src/cli/**`, `tests/cli/**` | CLI 可以创建并读取笔记；integration PASS |
| N1-04 | 1 | N1 release gate | BACKLOG | — | N1-03 | COMPLEX | HIGH | integration tests, docs | main 全测通过；status/roadmap 同步 |

只有 N1-02 可以领取。

## 2. Coordinator 领取 N1-02

Coordinator 先检查：

```text
git status          clean
git worktree list   无 N1-02
main HEAD           abc1234
N1-01               DONE
N1-02               READY / 无 Owner
```

然后把 N1-02 更新为：

```text
Revision: 1
Status: IN_PROGRESS
Owner: scheduled-agent
Claim ID: N1-02-r1-claim-001
Claimed At: <ISO-8601>
Branch: codex/n1-02-file-repository
Worktree: <WORKTREE_PATH>
Base Commit: abc1234
```

领取前由 scheduled-agent 获取短时 Coordinator 原子锁；持锁写入 Claim 并提交协调状态，重新读取 Task Board 和 main 确认 Claim 仍属于 scheduled-agent 后释放锁，再基于最新 main 创建 worktree：

```bash
git worktree add ../note-app-n1-02 -b codex/n1-02-file-repository main
```

## 3. Worker 实现

Worker 只允许修改：

```text
src/storage/**
tests/storage/**
```

明确不做：

- CLI 接线；
- 修改 Note contract；
- 修改 Task Board；
- 引入数据库；
- 顺手实现 N1-03。

Worker 先写 repository contract tests，再实现文件存储、原子替换和损坏文件错误。完成后运行项目规定的类型检查和测试，检查 diff 并提交。

Handoff：

```text
Task: N1-02
Revision: 1
Attempt: N1-02-r1-a1
Status: READY_FOR_REVIEW
Branch: codex/n1-02-file-repository
Commit: def5678
Changed:
- src/storage/file-repository.ts
- tests/storage/file-repository.test.ts
Tests:
- typecheck / exit 0 / PASS evidence
- storage contract / exit 0 / PASS evidence
- full unit suite / exit 0 / PASS evidence
Notes:
- 无共享文件接线
```

Task 进入 `REVIEW`，此时仍不能标记 DONE。

## 4. Integrator 集成

Integrator：

1. 检查 `def5678` 只修改 Allowed Paths。
2. 检查文件写入和错误处理满足 Acceptance。
3. 在 Task branch 复跑相关测试。
4. 按项目规则合入 `main`。
5. 在 `main` 重新运行 typecheck、storage contract 和完整单元测试。

如果 main 复验失败，N1-02 保持 `REVIEW` 或进入 `BLOCKED`，不能用文档把失败掩盖成 DONE。

## 5. N1-02 DONE 并解锁下一任务

main 复验通过后更新 Task Board：

| ID | Rev | Task | Status | Owner | Depends On | Complexity | Risk | Allowed Paths | Acceptance |
|---|---:|---|---|---|---|---|---|---|---|
| N1-01 | 1 | Note / Notebook contracts | DONE | agent-a | — | STANDARD | MEDIUM | `src/domain/**`, tests | contract tests PASS |
| N1-02 | 1 | File repository | DONE | scheduled-agent | N1-01 | STANDARD | MEDIUM | `src/storage/**`, `tests/storage/**` | main 上 create/read/update/reopen 和损坏文件测试 PASS |
| N1-03 | 1 | CLI integration | READY | — | N1-02 | SIMPLE | LOW | `src/cli/**`, `tests/cli/**` | CLI 可以创建并读取笔记；integration PASS |
| N1-04 | 1 | N1 release gate | BACKLOG | — | N1-03 | COMPLEX | HIGH | integration tests, docs | main 全测通过；status/roadmap 同步 |

status 中唯一 NEXT 改为 N1-03。N1-04 仍不能领取。

## 6. 如果中途出现重大问题

假设实现时发现“笔记是否默认端到端加密”尚未决定，而且不同选择会改变存储格式、密钥管理和迁移策略。Agent 应：

1. 创建 `ND-001 — 本地笔记加密边界`。
2. 列出方案、影响和推荐。
3. N1-02 → `BLOCKED`，记录 `Block Scope: TASK`。
4. 写清“用户确认存储安全模型并同步到 spec/ADR 后恢复”。
5. 保存安全进度；如果还有不依赖 N1-02 的 READY Task，可以继续那些任务。

相反，普通的路径拼接 bug 或临时文件清理错误应由 Worker 直接修复，不创建人工决策。

## 7. 示例证明了什么

- READY 来自依赖和阶段 Gate，不来自 Agent 猜测。
- 领取发生在实现之前，并固定 Owner 和隔离工作区。
- Worker 不越界实现后续任务。
- branch 测试通过只进入 REVIEW。
- main 复验通过后才 DONE。
- DONE 会解锁下一任务并同步唯一 NEXT。
- 重大方向问题会留下可恢复的 Decision，而不是藏在聊天里。
