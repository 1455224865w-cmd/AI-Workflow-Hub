# 路线

## 远程仓库

- 仓库：https://github.com/1455224865w-cmd/AI-Workflow-Hub
- `main` 已推送初始提交 `bf87e74`。
- CI 工作流是 `.github/workflows/ci.yml`，只安装项目并运行 `pytest`。
- 首次推送的运行已成功：https://github.com/1455224865w-cmd/AI-Workflow-Hub/actions/runs/44689668267
- Milestone「0.2 下一步」跟踪下面三个 Issue：
  - #1 用 PostgreSQL 保存运行状态
  - #2 增加不绑定厂商的模型提供方接口
  - #3 提供可导入的工作流模板
## 已完成：0.1.0

YAML 校验、条件、受限 script、HTTP 防护、重试、超时、审批暂停和按已成功节点恢复。

## 下一步

1. 把运行状态放到 PostgreSQL，进程重启后仍能恢复。
2. 增加模型提供方接口。引擎不保存某一家的密钥格式。
3. 提供可导入的 CI 失败分析和发布说明模板。

## 暂不做

可视化编辑器、并行节点和分布式执行。
