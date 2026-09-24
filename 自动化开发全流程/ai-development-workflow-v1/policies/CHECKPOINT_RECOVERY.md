# Checkpoint & Recovery

Task checkpoint 记录目标、已完成、文件、命令结果、失败 fingerprint、未完成和下一动作；Stage/Phase checkpoint 另记录 Gate、集成状态、风险和决策。中断恢复顺序：读取 AGENTS/规则 → CURRENT_STATE → checkpoint → 当前计划/契约 → Git HEAD 与 dirty state → 运行最小验证。

未决人工请求及失败计数必须保留；恢复不能把等待决策的工作直接转为可执行。没有 Git 时明确记录无 Git 基线，并核对文件差异。

Session 不可靠，Git HEAD + dirty state + 文档才是真源。发现未归属改动先保留并询问/隔离，不擅自覆盖或清理。
