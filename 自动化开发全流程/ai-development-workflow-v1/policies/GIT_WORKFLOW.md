# Git Workflow

开始前记录基线 HEAD 和 dirty state。保留用户已有改动；不要用 reset/checkout 覆盖它们。分支和提交按项目约定，Task 不强制一 Task 一提交。建议在 Stage/Phase Gate 或可恢复节点提交 checkpoint；提交信息包含范围和验证。完成时报告 HEAD、dirty state、未提交改动和未验证项。
