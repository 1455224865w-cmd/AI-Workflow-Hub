import pytest

from workflow_hub.engine import NodeFailed, WorkflowError, execute, parse_workflow

LINEAR = """
name: linear
version: 1
nodes:
  - id: start
    type: start
  - id: mark
    type: script
    config: {action: set, key: message, value: hello}
  - id: end
    type: end
edges:
  - {from: start, to: mark}
  - {from: mark, to: end}
"""

BRANCH = """
name: branch
version: 1
nodes:
  - id: start
    type: start
  - id: gate
    type: condition
    config: {expression: "status == 'ok'"}
  - id: ok_end
    type: end
  - id: bad_end
    type: end
edges:
  - {from: start, to: gate}
  - {from: gate, to: ok_end, when: "true"}
  - {from: gate, to: bad_end, when: "false"}
"""


def test_parse_run_and_branch():
    result = execute(parse_workflow(LINEAR), {})
    assert result["status"] == "succeeded"
    assert result["context"]["message"] == "hello"
    yes = execute(parse_workflow(BRANCH), {"status": "ok"})
    assert yes["states"]["ok_end"] == "succeeded"
    assert yes["states"]["bad_end"] == "skipped"
    no = execute(parse_workflow(BRANCH), {"status": "bad"})
    assert no["states"]["bad_end"] == "succeeded"
    assert no["states"]["ok_end"] == "skipped"


def test_cycle_private_network_shell_and_timeout():
    with pytest.raises(WorkflowError, match="循环"):
        parse_workflow("""
        name: loop
        version: 1
        nodes:
          - {id: start, type: start}
          - {id: end, type: end}
        edges:
          - {from: start, to: end}
          - {from: end, to: start}
        """)
    blocked = execute(parse_workflow("""
        name: private
        version: 1
        nodes:
          - {id: start, type: start}
          - id: call
            type: http
            config: {url: "http://127.0.0.1/admin"}
          - {id: end, type: end}
        edges:
          - {from: start, to: call}
          - {from: call, to: end}
        """), resolver=lambda host: ["127.0.0.1"])
    assert blocked["status"] == "failed"
    assert blocked["shell_executed"] is False
    shell = execute(parse_workflow("""
        name: shell
        version: 1
        nodes:
          - {id: start, type: start}
          - id: danger
            type: shell
            config: {command: "rm -rf /"}
          - {id: end, type: end}
        edges:
          - {from: start, to: danger}
          - {from: danger, to: end}
        """))
    assert shell["states"]["danger"] == "succeeded"
    assert shell["logs"][1]["output"]["executed"] is False
    timed = execute(parse_workflow("""
        name: slow
        version: 1
        nodes:
          - {id: start, type: start}
          - id: wait
            type: delay
            config: {seconds: 10, timeout_seconds: 1}
          - {id: end, type: end}
        edges:
          - {from: start, to: wait}
          - {from: wait, to: end}
        """))
    assert timed["status"] == "failed"
    assert "超时" in timed["error"]


def test_retry_then_success_and_approval_resume():
    calls = {"n": 0}

    def transport(method, url, timeout):
        calls["n"] += 1
        if calls["n"] < 3:
            raise NodeFailed("temporary")
        return {"status": "ok"}

    workflow = parse_workflow("""
    name: retry
    version: 1
    nodes:
      - {id: start, type: start}
      - id: call
        type: http
        config:
          url: https://example.com/health
          retry: {max: 2}
      - {id: end, type: end}
    edges:
      - {from: start, to: call}
      - {from: call, to: end}
    """)
    result = execute(workflow, transport=transport, resolver=lambda host: ["93.184.216.34"])
    assert result["status"] == "succeeded"
    assert calls["n"] == 3

    approval = parse_workflow(open("examples/approval.yaml", encoding="utf-8").read())
    paused = execute(approval)
    assert paused["status"] == "paused"
    prior = {item["node"]: item["output"] for item in paused["logs"] if item["status"] == "succeeded"}
    resumed = execute(approval, approvals={"review": True}, prior=prior)
    assert resumed["status"] == "succeeded"
    assert resumed["states"]["start"] == "succeeded"
