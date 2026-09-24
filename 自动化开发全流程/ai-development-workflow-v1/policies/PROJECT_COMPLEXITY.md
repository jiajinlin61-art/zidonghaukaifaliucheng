# Project Complexity

TRIVIAL：文字/配置/机械单点 → FAST。

SIMPLE：单模块小功能、低风险 → FAST，必要时 STANDARD。

STANDARD：多文件、明确能力、需要测试/集成 → STANDARD。

COMPLEX：跨模块、长期、外部依赖或高不确定性 → FULL。

CRITICAL：安全、财务、生产、个人数据、不可逆或监管影响 → FULL + 更严格人工批准。若指标冲突，按更高复杂度；可在范围收窄并记录后降级。
