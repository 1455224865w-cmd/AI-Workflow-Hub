from pathlib import Path

import pytest

from workflow_hub.engine import WorkflowError, execute, parse_workflow
from workflow_hub.store import RunStore

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class Provider:
    def __init__(self):
        self.prompts = []
        self.calls = 0

    def complete(self, prompt):
        self.calls += 1
        self.prompts.append(prompt)
        return "已记录"


def test_templates_parse_and_run_without_shell():
    paths = [EXAMPLES / "ci-failure.yaml", EXAMPLES / "release-notes.yaml"]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "type: shell" not in text
        workflow = parse_workflow(text)
        result = execute(workflow, {"ready": True})
        assert result["status"] == "succeeded"
        assert result["shell_executed"] is False


def test_agent_requires_provider_and_does_not_call_network():
    workflow = parse_workflow("""
    name: agent
    version: 1
    nodes:
      - {id: start, type: start}
      - id: ask
        type: agent
        config: {prompt: "总结这次失败"}
      - {id: end, type: end}
    edges:
      - {from: start, to: ask}
      - {from: ask, to: end}
    """)
    missing = execute(workflow)
    assert missing["status"] == "failed"
    assert "拒绝发送请求" in missing["error"]
    provider = Provider()
    done = execute(workflow, provider=provider)
    assert done["status"] == "succeeded"
    assert provider.prompts == ["总结这次失败"]
    assert done["logs"][1]["output"]["text"] == "已记录"


def test_run_store_reopens(tmp_path):
    path = str(tmp_path / "runs.sqlite3")
    workflow = parse_workflow((EXAMPLES / "approval.yaml").read_text(encoding="utf-8"))
    paused = execute(workflow)
    store = RunStore(path)
    store.save("run-1", {"workflow_name": paused["name"], "status": paused["status"]})
    reopened = RunStore(path)
    assert reopened.get("run-1")["status"] == "paused"
