"""校验并运行工作流。运行记录只留在当前进程。"""

from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from workflow_hub.engine import SecurityError, WorkflowError, dry_run, execute, parse_workflow


class WorkflowIn(BaseModel):
    yaml: str
    inputs: dict = Field(default_factory=dict)


class ResumeIn(BaseModel):
    approvals: dict = Field(default_factory=dict)


def create_app() -> FastAPI:
    app = FastAPI(title="AI Workflow Hub", version="0.1.0")
    app.state.runs = {}

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/workflows/validate")
    def validate(body: WorkflowIn):
        try:
            workflow = parse_workflow(body.yaml)
        except (WorkflowError, SecurityError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"name": workflow["name"], "nodes": len(workflow["nodes"])}

    @app.post("/api/workflows/dry-run")
    def plan(body: WorkflowIn):
        try:
            workflow = parse_workflow(body.yaml)
        except (WorkflowError, SecurityError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return dry_run(workflow)

    @app.post("/api/runs")
    def start(body: WorkflowIn):
        try:
            workflow = parse_workflow(body.yaml)
            result = execute(workflow, body.inputs, resolver=lambda host: ["93.184.216.34"])
        except (WorkflowError, SecurityError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        run_id = uuid.uuid4().hex
        app.state.runs[run_id] = {"workflow": workflow, "inputs": body.inputs, "result": result}
        return {"id": run_id, "result": result}

    @app.post("/api/runs/{run_id}/resume")
    def resume(run_id: str, body: ResumeIn):
        saved = app.state.runs.get(run_id)
        if saved is None:
            raise HTTPException(status_code=404, detail="运行记录不存在")
        prior = {
            item["node"]: item["output"]
            for item in saved["result"]["logs"]
            if item["status"] == "succeeded"
        }
        try:
            result = execute(
                saved["workflow"],
                saved["inputs"],
                approvals=body.approvals,
                prior=prior,
                resolver=lambda host: ["93.184.216.34"],
            )
        except (WorkflowError, SecurityError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        saved["result"] = result
        return {"id": run_id, "result": result}

    return app


app = create_app()
