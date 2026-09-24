# Model Routing

## 1. 分层原则

模型路由属于执行层，不属于项目级 Task Board。

- Project Controller 决定项目目标、Roadmap、依赖、READY/BLOCKED/DONE。
- Execution Engine 接收一个 Task Contract，决定具体 role/profile/backend/model。
- Role 表示职责：planner / worker / debugger / reviewer。
- Profile 表示能力需求，例如 coding-standard、debug-deep。
- Binding 才表示物理执行：Codex + GPT，或 Claude Code + GLM。

因此 Task Contract 默认只写 Complexity、Risk 和可选 Profile Override，不把具体模型写死。

## 2. Profile

| Profile | Role | 默认用途 |
|---|---|---|
| planning-deep | planner | PRD、架构、Phase/Stage、复杂方案 |
| coding-economy | worker | 机械、低风险、范围很小 |
| coding-fast | worker | 简单功能、快速迭代 |
| coding-standard | worker | 日常跨文件开发 |
| coding-complex | worker | 长上下文、跨模块、复杂逻辑 |
| coding-critical | worker | 高风险核心逻辑、关键状态机 |
| visual-coding | worker | UI/截图/图像参与的实现任务 |
| debug-standard | debugger | 常规 Debug |
| debug-deep | debugger | 跨模块、难复现、长链路 Debug |
| review-standard | reviewer | 普通独立 Review |
| review-critical | reviewer | 高风险/关键任务 Review |

物理候选绑定见 routing/MODEL_BINDINGS.yaml。

## 3. 当前本机绑定基线

本机 Claude Code 2.1.278 已配置并完成最小真实调用探测：

- GLM-5.1 → glm-5.1
- GLM-5.2 → glm-5.2[1M]
- GLM-5.3 → glm-5.3[1M]
- GLM-5.3-Flash → glm-5.3-flash[1M]

四个 GLM 候选均返回 ROUTE_OK。Claude Code 同时报告这些名称未收录在其内置 model catalog，因此会按当前自定义 provider/model mapping 使用，并可能对未知上下文窗口采用保守限制；这属于目录识别提示，不是本轮调用失败。

本机 Codex CLI 0.153.4 对 gpt-5.6-luna、gpt-5.6-terra、gpt-5.6-sol 均完成只读、ephemeral 最小真实调用探测并返回 ROUTE_OK。当前 binding 记录了探测时 CLI 版本、已探测模型列表和非敏感配置指纹；执行前仍需通过 route preflight。

## 4. 默认路由

执行任务：

- TRIVIAL + LOW → coding-economy → 首选 GLM-5.1。
- SIMPLE + LOW → coding-fast → 首选 GLM-5.3-Flash。
- STANDARD + LOW/MEDIUM → coding-standard → 首选 GLM-5.2。
- HIGH risk，或 COMPLEX 且风险非 CRITICAL → coding-complex → 首选 GLM-5.3。
- CRITICAL complexity/risk → coding-critical → 首选 GPT-5.6 Sol。
- 视觉参与、复杂度不高且风险为 LOW/MEDIUM → visual-coding → 首选 GLM-5.3-Flash；HIGH/CRITICAL 风险不走 Flash 快速路由。

Debug：

- 常规 → debug-standard。
- COMPLEX/HIGH risk，或同一 fingerprint 已失败两次 → debug-deep。

Review：

- 普通 → review-standard。
- HIGH/CRITICAL risk 或 CRITICAL complexity → review-critical。
- 有兼容候选时优先选择与 Worker 不同的 backend/model family。

## 5. 失败升级

模型升级不是第一次失败后的默认动作。

1. 首次 attempt 失败：记录 fingerprint 和 attempt context。
2. 第 1 次 retry：保留当前 Profile，基于新证据修复。
3. 同一 failure fingerprint 再次失败后，第 2 次 retry 才按 escalation 升一级。
4. 环境/依赖问题：先修环境，不靠升级模型掩盖。
5. 需求/输入歧义：进入 NEEDS_HUMAN，不靠更强模型猜。
6. 数据损失、凭据、权限、不可逆操作：立即停。
7. Retry Budget 耗尽：NEEDS_HUMAN。
8. 换 Session / 换模型 / 换 Executor 不能重置 failure count。

## 6. 独立 Review

Worker 的成功声明不是 Review 证据。Reviewer 必须使用独立 Session，并读取 Task Contract、diff 和真实验证输出。

推荐：

- Claude Code Worker → Codex Reviewer。
- Codex Worker → Claude Code Reviewer。
- 高风险任务 → review-critical；无法使用跨 backend 时允许同 backend 不同 Session，但必须记录原因。

## 7. 路由器

参考实现：

PowerShell:
  .\.venv\Scripts\python.exe tools/model_router.py --purpose execute --complexity STANDARD --risk MEDIUM

Review 示例：
  .\.venv\Scripts\python.exe tools/model_router.py --purpose review --complexity STANDARD --risk MEDIUM --worker-backend claude-code

输出包含 role、profile、backend、model、effort、verification、command_hint。

真正执行前再运行：

```powershell
.\.venv\Scripts\python.exe tools/route_preflight.py --purpose execute --complexity STANDARD --risk MEDIUM
```

Preflight 检查当前 backend executable、CLI 版本、非敏感本地配置指纹、probe 记录是否未过期，以及所选模型是否仍在当前 probe 记录中。它不会再次调用远端模型，因此只能证明“已有 probe 记录仍与当前本地执行环境兼容”，不能替代新的端到端模型调用。CLI、Provider/本地配置、Model ID 变化或 probe 超过有效期后，应重新做真实 probe 并更新绑定记录。

Profile Override 只在上层明确有理由时使用，并记录 override reason。Router 会验证职责和最低能力：override 可以升级，但不能把 CRITICAL/HIGH-risk 任务降到低能力 Profile，也不能把 Reviewer override 成 Worker Profile。

自动候选还必须满足 verification policy。只有被当前配置允许的已验证候选才能自动执行；仅在配置里“看见”的模型不能自动选中。Backend 版本、Provider endpoint、凭据或 Model ID 改变后，应重新做最小探测并更新 binding verification。

## 8. Backend 调用边界

Codex CLI 支持 --model，reasoning effort 通过 config override 传入；Claude Code 支持 --model 与 --effort。

Router 只产生 route 和 command hint，不自动绕过权限、不自动扩大 writable workspace，也不负责项目级 Task 状态。真正执行前仍需遵守 Executor、Approval、Allowed Paths 和 Quality Gate 规则。

## 9. Hard Route Gate

Model Routing 是执行门禁，不是建议。每个实现 Task 在启动 Worker 前必须完成：

1. 调用 model_router.py 得到确定性 execution route；
2. 基于 Worker backend 再解析 review route；
3. 分别运行 route_preflight.py；
4. 将两个 resolved route 及 preflight command / exit_code / evidence 写入 Execution Request 1.4；
5. 使用 execution_contract_validate.py actual 模式通过契约校验后，才能启动 Worker。

delegated Worker 的实际 profile/backend/model/effort 必须和 resolved_execution 完全一致，并记录独立 session 与真实 invocation evidence。只在文档里声称“用了 GLM/GPT”但没有实际调用证据，视为 Route Gate FAIL。

Controller 默认不得充当 Worker。若用户明确指定 Controller 直接实现或所有兼容 Worker backend 不可用，可使用 controller_worker_override，但必须在 Request 中显式授权并写明原因。静默 fallback 到当前 Controller 禁止。

Reviewer 同样必须与 resolved_review 一致；模型 Reviewer 必须是独立 Session，并记录真实 invocation evidence。
