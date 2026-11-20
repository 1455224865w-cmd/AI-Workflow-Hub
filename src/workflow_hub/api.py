"""校验并运行工作流。传入数据库路径时，运行记录可以在新进程里打开。"""

from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from workflow_hub.engine import SecurityError, WorkflowError, dry_run, execute, parse_workflow
from workflow_hub.store import RunStore


class WorkflowIn(BaseModel):
    yaml: str
    inputs: dict = Field(default_factory=dict)


class ResumeIn(BaseModel):
    approvals: dict = Field(default_factory=dict)


def create_app(db_path: str | None = None) -> FastAPI:
    app = FastAPI(title="AI Workflow Hub", version="0.1.0")
    app.state.runs = {}
    app.state.store = RunStore(db_path) if db_path else None

    def remember(run_id: str, payload: dict) -> None:
        app.state.runs[run_id] = payload
        if app.state.store is not None:
            app.state.store.save(run_id, payload)

    def load(run_id: str) -> dict | None:
        saved = app.state.runs.get(run_id)
        if saved is None and app.state.store is not None:
            saved = app.state.store.get(run_id)
            if saved is not None:
                app.state.runs[run_id] = saved
        return saved

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
        remember(run_id, {"workflow": workflow, "inputs": body.inputs, "result": result})
        return {"id": run_id, "result": result}

    @app.post("/api/runs/{run_id}/resume")
    def resume(run_id: str, body: ResumeIn):
        saved = load(run_id)
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
        remember(run_id, saved)
        return {"id": run_id, "result": result}

    return app


app = create_app()
