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
