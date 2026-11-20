# AI Workflow Hub

工作流负责顺序、分支、重试和审批。节点只做一件受限的事。当前版本不绑定模型厂商，也没有可视化编辑器。

## 0.1.0 能做什么

- 解析并校验 version 1 的 YAML：唯一的 start、至少一个 end、无环、节点不超过 100 个。
- 运行 start、end、condition、script、http、delay、approval 和 shell。
- condition 使用自写表达式，只支持比较、与或非和括号，不调用 `eval`。
- script 只允许 `action: set`。
- http 拒绝本机、内网和链路本地地址。库函数默认没有传输器，因此不会自己发请求。
- shell 节点只记录“未执行”，不会启动进程。
- 重试最多 5 次。delay 超过 `timeout_seconds` 会失败。
- approval 会暂停。带上已成功节点的输出和审批结果后可以继续。

## 限制

- 恢复会跳过已成功节点，但没有独立的数据库持久化。
- 没有并行节点，也没有图形编辑器。
- API 进程重启后，内存里的运行记录会消失。

工作流字段见 `docs/architecture/workflow-spec.md`。

## 本地运行

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest
uvicorn workflow_hub.api:app --reload
```

## 许可证

Apache-2.0。

## 语言和 Spring AI

默认语言是中文。请求带 `Accept-Language: en` 或 `?lang=en` 时，错误信息和工具说明返回英文。源码、SQL、日志原文不翻译。

Spring AI 不内嵌在本服务里。把 `spring-ai/pom-snippet.xml` 的 `spring-ai-starter-mcp-client` 加到 Spring AI 应用，并使用 `spring-ai/application-mcp.yml` 的 Streamable HTTP 连接。端点是 `/mcp`。本仓库的测试覆盖 MCP 的 initialize、tools/list 和 tools/call，不编译 Java。
