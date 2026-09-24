# <PROJECT_NAME> — Current Status

> 更新时间：YYYY-MM-DD。项目级当前阶段、NEXT 和已集成事实的权威来源。执行 attempt、模型路由、失败计数和 Review 证据由 Execution Result/checkpoint 记录，不在本文件维护第二份。

<!-- project-stage: P1 -->
<!-- project-next: P1-01 -->

## 1. 当前阶段

```text
P0  <阶段名称>  VALIDATED
P1  <阶段名称>  ACTIVE
P2  <阶段名称>  GATED BY P1 VALIDATED
```

## 2. 当前真实状态

- 已完成并验证：<事实和证据>。
- 当前仍未完成：<事实>。
- 当前不存在/存在的 blocker：<说明>。
- 不要从历史文档推断 NEXT。

## 3. 当前 NEXT

```text
NOW: P1-01 READY
AFTER: P1-02 blocked by P1-01
```

具体范围和验收见 `docs/task-board.md` 与 `docs/development-plan.md`。

## 4. Git / Test 基线

```text
main HEAD: <COMMIT_OR_VERIFICATION_METHOD>
typecheck: <COMMAND_AND_RESULT>
unit tests: <COMMAND_AND_RESULT>
integration/build: <COMMAND_AND_RESULT_OR_NOT_APPLICABLE>
```

只记录实际执行过的结果，并注明时间或 commit。未执行的验收不得写成 PASS。

发生冲突时不要按“更新时间更新”直接覆盖：先核对 main HEAD、Task commit、worktree、测试证据和 Task Board，再修复状态。checkpoint 是恢复线索，不是项目级 NEXT 的权威来源。

## 5. 当前风险

- <风险、影响、观察方式或恢复条件>。
