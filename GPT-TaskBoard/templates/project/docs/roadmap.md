# <PROJECT_NAME> — Canonical Roadmap

> 本文件是阶段顺序和阶段目标的权威来源。当前进度见 `status.md`，具体执行见 `task-board.md`。

## 1. 阶段顺序

```text
P0 Foundation
  ↓ VALIDATED
P1 First Usable Slice
  ↓ VALIDATED
P2 Production Hardening
```

## 2. P0 — Foundation

**目标：** <阶段目标>
**状态：** VALIDATED

阶段验收：

- <已经通过的阶段级验收>；
- <对应证据位置>。

## 3. P1 — First Usable Slice

**目标：** <用户或系统可以完成的完整闭环>
**状态：** ACTIVE

进入条件：

- P0 VALIDATED。

阶段验收：

- <功能闭环>；
- <自动化测试/构建>；
- <文档和 Git 状态>；
- <必要人工验收>。

阶段验收全部通过后才能将 P1 标记为 VALIDATED，并释放 P2 的第一个任务。

## 4. P2 — Production Hardening

**目标：** <可靠性、安全、发布或规模目标>
**状态：** BACKLOG

进入条件：P1 VALIDATED。

## 5. 当前不进入主线

- <明确延后的功能或平台>；
- <为什么现在不做，以及未来重新评估的 Gate>。
