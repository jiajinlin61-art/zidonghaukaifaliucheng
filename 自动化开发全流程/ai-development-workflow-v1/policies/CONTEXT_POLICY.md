# Context Policy

优先级：当前 Task Contract → 相关源码/测试 → 最近 Review 与 checkpoint → Architecture/Plan → PRD/Brief → 历史摘要。只加载能影响当前决策的文件；不把整个仓库塞进上下文。

Context Budget 接近上限时停止扩展范围，更新摘要、验证结果、未决问题和下一动作到 checkpoint，再切 Session。历史摘要是线索，不是真源；以工作区、Git、契约和验证结果为准。
