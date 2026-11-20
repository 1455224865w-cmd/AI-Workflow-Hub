import json
from pathlib import Path

from fastapi.testclient import TestClient

from workflow_hub.api import create_app

ROOT = Path(__file__).resolve().parents[1]
YAML = """
name: plan
version: 1
nodes:
  - {id: start, type: start}
  - id: cmd
    type: shell
    config: {command: "rm -rf /", timeout_seconds: 5}
  - {id: end, type: end}
edges:
  - {from: start, to: cmd}
  - {from: cmd, to: end}
"""


def test_english_validation_and_dry_run_does_not_execute():
    client = TestClient(create_app())
    denied = client.post("/api/workflows/validate", json={"yaml": "name: x\nversion: 2\n"}, headers={"Accept-Language": "en"})
    assert denied.status_code == 400
    assert denied.json()["detail"] == "Only version: 1 is accepted"
    called = client.post("/mcp", json={
        "jsonrpc": "2.0", "id": 5, "method": "tools/call",
        "params": {"name": "workflow_dry_run", "arguments": {"yaml": YAML, "locale": "en"}},
    })
    payload = json.loads(called.json()["result"]["content"][0]["text"])
    assert payload["executed"] is False
    assert payload["network"] is False
    assert payload["shell_executed"] is False
    assert [step["type"] for step in payload["steps"]] == ["start", "shell", "end"]
    assert "does not call HTTP" in payload["message"]
    text = (ROOT / "spring-ai" / "application-mcp.yml").read_text(encoding="utf-8")
    sample = (ROOT / "nacos" / "spring-mcp.yaml").read_text(encoding="utf-8")
    assert "nacos:" in text
    assert "127.0.0.1" not in text
    assert "${MCP_SERVICE_URL}" in sample
