# 工作流定义 1

```yaml
name: 名称
version: 1
nodes:
  - id: start
    type: start
  - id: gate
    type: condition
    config:
      expression: "status == 'ok'"
      timeout_seconds: 30
  - id: done
    type: end
edges:
  - from: start
    to: gate
  - from: gate
    to: done
    when: "true"
```

节点类型：`start`、`end`、`condition`、`script`、`http`、`delay`、`approval`、`shell`。

`script.config.action` 只能是 `set`，并提供合法的 `key`。`http.config.url` 必须是 http 或 https，目标地址不能是内网。`shell` 不执行 `command`。`delay` 的 `seconds` 大于 `timeout_seconds` 时失败。`retry.max` 是额外重试次数，最大 5。

边的 `when` 只能省略、`true` 或 `false`。条件节点按表达式结果选择边。节点 id 不要使用 YAML 会当成布尔值的 `yes`、`no`、`on`、`off`。
