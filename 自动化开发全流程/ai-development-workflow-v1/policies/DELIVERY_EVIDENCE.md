# 交付证据操作（首次接入/排错时阅读）

只适用于明确启用完整规则包的业务项目。工具负责采集和检查一个命令，不负责调度任务、调用付费模型或批准业务结论。以下命令使用已核验的共享解释器和工具绝对路径，在业务工作区运行；先按 [共享使用边界](SHARED_LIBRARY_USAGE.md) 核对权限和输出归属。

```powershell
# 替换项目路径；在该业务工作区执行。此设置不代替子进程权限隔离。
$workflowRoot = 'E:\自动化开发任务通用流程\自动化开发全流程'
$workflowPython = Join-Path $workflowRoot '.venv\Scripts\python.exe'
$workflowTools = Join-Path $workflowRoot 'tools'
$env:PYTHONDONTWRITEBYTECODE = '1'
```

## 一次性约定

- 契约版本 1.4。Request/Result 来自模板，业务目标、scope、审批、resolved route、session 和结论按事实填写。
- 证据目录必须在任务工作区和共享库之外，每个项目使用专属目录，再按 task/attempt 分开；receipt 名称唯一。不要覆盖旧记录，不把凭据放命令参数或日志中。
- Git 交付必须已提交且工作区干净，baseline→HEAD 差异须与捕获改动一致；有用户原有未提交修改时先使用隔离工作区，不擅自提交/清理这些修改。Git 交付使用完整 HEAD 提交号；no-git 使用完整内容摘要。Git 快照包含 tracked 与未忽略 untracked，排除被忽略且未跟踪的生成物；无 Git 排除 .git/.venv/node_modules/__pycache__/.pytest_cache。
- 交付源码和验收依赖文件必须可被快照覆盖，不把业务源文件加入忽略列表；子模块/链接目录需要独立任务，当前工具遇到无法核实的路径会失败。
- 日志及 snapshot 是本地可核查记录，不是防篡改签名。能同时改写 receipt 和日志的主体仍可伪造它们；独立审查/权限隔离与模型预检仍必需。命令记录证明进程运行，不单独证明服务端实际模型身份。

## 1. 包装真实执行命令

```powershell
& $workflowPython -B (Join-Path $workflowTools 'delivery_evidence.py') --workspace E:\project --evidence-root E:\task-evidence\project-unique-id\T1-a1 --name worker --task-id T1 --task-revision 1 --attempt-id T1-r1-a1 --kind worker --timeout 3600 -- ACTUAL_EXECUTABLE ACTUAL_ARGUMENTS
```

ACTUAL_EXECUTABLE/ARGUMENTS 替换成已解析执行者的真实命令；直接传参，不使用 shell=True。脚本需要 PowerShell 时明确调用 pwsh -File。工具等待该命令结束，记录 stdout/stderr、真实退出码、超时、前后内容摘要和 changed_paths；默认只输出小型摘要。进程后台脱离运行不能视为完成。

工具保留任务开始时已有的 dirty 文件，只将前后变化归入任务。执行命令不得改动未授权文件；校验器会对照实际差异检查 scope，但它不是操作系统沙箱，也不自动恢复被修改的文件。

## 2. 验证与审查

用同一命令包装 required check，kind 改成 check:V1、name 改成 check-V1；review 使用独立执行者、kind=review、name=review。只运行真实批准的检查，不为了生成记录执行空命令。

命令采用 argv，记录中的 command 是 subprocess.list2cmdline 的显示形式。定义 Request 的 required command 时使用相同显示形式；不能事后把失败的必需检查替换为更容易通过的检查。

Git 验证和审查须在最终交付提交之后采集；新增提交也会使旧检查失效。验证与审查不得更改被快照覆盖的交付文件。测试缓存、编译产物使用合理忽略目录。修复属于新的 Worker 执行，之后重新采集验证/审查证据。

语义检查和人工审查先保存具体报告到证据目录，再用下一节命令自动生成报告记录。记录文件内绑定 task/revision/attempt、check ID、工作区、内容和提交，并保存原报告哈希；业务判断仍由实际审查者负责。不要伪造模型 invocation。

所有 REQUEST.yaml、RESULT.yaml、PROJECT_ACCEPTANCE.yaml 和 EVIDENCE_DIR 均为占位，实际调用替换成本项目绝对路径；不得直接更新共享 templates 中的原件。

## 3. 自动填充已有 Result

```powershell
& $workflowPython -B (Join-Path $workflowTools 'evidence_result_update.py') --request REQUEST.yaml --result RESULT.yaml --evidence-root EVIDENCE_DIR --worker worker.json --check V1=check-V1.json
& $workflowPython -B (Join-Path $workflowTools 'evidence_result_update.py') --request REQUEST.yaml --result RESULT.yaml --evidence-root EVIDENCE_DIR --review review.json
# 仅在有对应真实报告时，绑定语义检查/人工审查；不会生成结论：
& $workflowPython -B (Join-Path $workflowTools 'evidence_result_update.py') --request REQUEST.yaml --result RESULT.yaml --evidence-root EVIDENCE_DIR --semantic V2=semantic-V2.txt
& $workflowPython -B (Join-Path $workflowTools 'evidence_result_update.py') --request REQUEST.yaml --result RESULT.yaml --evidence-root EVIDENCE_DIR --human-review human-review.txt
```

工具仅填入实际采集字段，不自动宣称完成，不选择模型，不生成审查结论。Result 采用同目录临时文件写完后原子替换，写入失败保留原结果。它保留其它字段；session、route、独立性和业务结论仍须来自真实执行者。失败 receipt 可以记录进 Result，但成功门禁不会接受失败退出码。

完成审查后 review.reviewed_content_sha256 必须等于 delivery.content_sha256；Git 下 reviewed_commit 必须等于 delivery.commit 且与审查 receipt 的提交一致。review_revision 是审查轮次，task_revision 通过 receipt 身份绑定，二者不是同一个字段。

## 4. 实际门禁

```powershell
& $workflowPython -B (Join-Path $workflowTools 'execution_contract_validate.py') --request REQUEST.yaml --result RESULT.yaml --evidence-root EVIDENCE_DIR
```

actual 为默认模式；成功 Result 必须同时提供 Request 和 evidence-root。检查身份、scope、route、检查覆盖、真实日志哈希、退出码、工作区内容、changed_paths 和审查提交。template 仅检验模板结构；直接调用 validate_request/result/pair 也仅做内存结构校验，不能代替 actual CLI。

1.3 的历史结果缺少实际证据时不能填上 1.4 版本号冒充迁移；保留历史记录，重新采集所需验证/审查或明确未验证。

## 5. 跨任务集成

多任务项目按 templates/PROJECT_ACCEPTANCE.yaml 将批准需求映射到任务和集成检查；FAST 直接复用当前 Task，不额外制造文件。

```powershell
& $workflowPython -B (Join-Path $workflowTools 'project_acceptance_validate.py') PROJECT_ACCEPTANCE.yaml --coverage-only
& $workflowPython -B (Join-Path $workflowTools 'project_acceptance_validate.py') PROJECT_ACCEPTANCE.yaml --evidence-root INTEGRATION_EVIDENCE_DIR
```

第一条只检查映射，不是验收。第二条还要求集成检查 receipt 属于当前集成 identity/工作区/内容/提交且成功；项目整合后采集新记录，不能拿各个旧任务检查的总和替代。UI 项目至少有一条真实用户路径；外部系统不可用时明确未验证，不能用模拟结果冒充实际接通。

映射工具不证明 Task 已完成，也不自动更新 DONE。Controller 还要核对任务交付、独立 Review、批准范围和未决问题。
