import pytest

from workflow_hub.engine import WorkflowError, dry_run, execute, parse_workflow


def test_dry_run_lists_order_without_calling_out():
    workflow = parse_workflow("""
    name: plan
    version: 1
    nodes:
      - {id: start, type: start}
      - id: call
        type: http
        config:
          url: https://example.com/health
          timeout_seconds: 5
      - {id: end, type: end}
    edges:
      - {from: start, to: call}
      - {from: call, to: end}
    """)

    def transport(*args, **kwargs):
        raise AssertionError("空跑不应访问网络")

    plan = dry_run(workflow)
    assert plan["order"] == ["start", "call", "end"]
    assert plan["executed"] is False
    assert plan["network"] is False
    assert plan["shell_executed"] is False
    with pytest.raises(AssertionError):
        transport()


def test_denied_approval_fails_closed():
    workflow = parse_workflow("""
    name: approval-demo
    version: 1
    nodes:
      - {id: start, type: start}
      - {id: review, type: approval}
      - {id: end, type: end}
    edges:
      - {from: start, to: review}
      - {from: review, to: end}
    """)
    denied = execute(workflow, approvals={"review": {"approved": False, "by": "ada"}})
    assert denied["status"] == "failed"
    assert denied["shell_executed"] is False
    assert denied["states"]["end"] != "succeeded"


def test_required_input_secret_and_dry_run_api():
    import json
    from fastapi.testclient import TestClient
    from workflow_hub.api import create_app

    token = "ghp_" + "c" * 36
    workflow = parse_workflow(f"""
    name: guarded
    version: 1
    inputs:
      - {{name: ready, required: true}}
    nodes:
      - {{id: start, type: start}}
      - id: note
        type: script
        config:
          action: set
          key: note
          value: "{token}"
      - {{id: end, type: end}}
    edges:
      - {{from: start, to: note}}
      - {{from: note, to: end}}
    """)
    with pytest.raises(WorkflowError):
        execute(workflow, {})
    plan = dry_run(workflow)
    assert plan["executed"] is False
    assert plan["network"] is False
    result = execute(workflow, {"ready": True})
    assert result["status"] == "succeeded"
    assert result["context"]["note"] == "[REDACTED_TOKEN]"
    assert token not in json.dumps(result)
    client = TestClient(create_app())
    response = client.post("/api/workflows/dry-run", json={"yaml": """
name: plan
version: 1
nodes:
  - {id: start, type: start}
  - {id: end, type: end}
edges:
  - {from: start, to: end}
"""})
    assert response.status_code == 200
    assert response.json()["order"] == ["start", "end"]
    assert response.json()["executed"] is False


def test_dry_run_shows_shell_without_executing_it():
    workflow = parse_workflow("""
    name: risky
    version: 1
    nodes:
      - {id: start, type: start}
      - id: wait
        type: delay
        config: {seconds: 0, timeout_seconds: 5}
      - id: cmd
        type: shell
        config: {command: "rm -rf /", timeout_seconds: 5}
      - {id: end, type: end}
    edges:
      - {from: start, to: wait}
      - {from: wait, to: cmd}
      - {from: cmd, to: end}
    """)
    plan = dry_run(workflow)
    assert [step["type"] for step in plan["steps"]] == ["start", "delay", "shell", "end"]
    assert plan["executed"] is False
    assert plan["shell_executed"] is False
    result = execute(workflow)
    assert result["shell_executed"] is False
    assert result["status"] == "succeeded"
    negative = parse_workflow("""
    name: bad-wait
    version: 1
    nodes:
      - {id: start, type: start}
      - id: wait
        type: delay
        config: {seconds: -1, timeout_seconds: 5}
      - {id: end, type: end}
    edges:
      - {from: start, to: wait}
      - {from: wait, to: end}
    """)
    failed = execute(negative)
    assert failed["status"] == "failed"
