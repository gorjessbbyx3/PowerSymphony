"""Model Fine-Tuning — REST API routes for OpenAI fine-tuning management."""

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/fine-tuning", tags=["fine_tuning"])


class UploadDatasetRequest(BaseModel):
    training_data: str
    filename: str = "training_data.jsonl"


class CreateJobRequest(BaseModel):
    file_id: str
    base_model: str = "gpt-4o-mini"
    n_epochs: int = 3
    suffix: str = ""


def _run_tool(func_name: str, **kwargs) -> Any:
    try:
        import importlib
        mod = importlib.import_module("functions.function_calling.fine_tuning")
        fn = getattr(mod, func_name)
        result = fn(**kwargs)
        return json.loads(result) if isinstance(result, str) else result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/upload")
async def upload_dataset(req: UploadDatasetRequest) -> Dict[str, Any]:
    """Upload a fine-tuning training dataset to OpenAI."""
    result = _run_tool("finetune_upload_dataset",
                        training_data=req.training_data, filename=req.filename)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"ok": True, **result}


@router.post("/jobs")
async def create_job(req: CreateJobRequest) -> Dict[str, Any]:
    """Start a fine-tuning job."""
    result = _run_tool("finetune_create_job",
                        file_id=req.file_id, base_model=req.base_model,
                        n_epochs=req.n_epochs, suffix=req.suffix)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"ok": True, **result}


@router.get("/jobs")
async def list_jobs(limit: int = 10) -> Dict[str, Any]:
    """List recent fine-tuning jobs."""
    result = _run_tool("finetune_list_jobs", limit=limit)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"ok": True, **result}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> Dict[str, Any]:
    """Get the current status of a fine-tuning job."""
    result = _run_tool("finetune_get_job_status", job_id=job_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"ok": True, **result}


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str) -> Dict[str, Any]:
    """Cancel a running fine-tuning job."""
    result = _run_tool("finetune_cancel_job", job_id=job_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"ok": True, **result}


@router.get("/models")
async def list_models() -> Dict[str, Any]:
    """List all available fine-tuned models."""
    result = _run_tool("finetune_list_models")
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"ok": True, **result}


@router.get("/example-data")
async def get_example_data() -> Dict[str, Any]:
    """Return example training data in the correct JSONL format."""
    example_lines = [
        json.dumps({"messages": [
            {"role": "system", "content": "You are a helpful assistant for PowerSymphony workflows."},
            {"role": "user", "content": "How do I create a multi-agent workflow?"},
            {"role": "assistant", "content": "To create a multi-agent workflow in PowerSymphony, define a YAML file with multiple agent nodes connected by edges. Each agent has a role, model, and optional tools."}
        ]}),
        json.dumps({"messages": [
            {"role": "system", "content": "You are a helpful assistant for PowerSymphony workflows."},
            {"role": "user", "content": "What tools can agents use?"},
            {"role": "assistant", "content": "Agents in PowerSymphony can use tools from the function_calling directory including file operations, web scraping, GitHub API, CI/CD generation, live data fetching, code execution, and more."}
        ]}),
        json.dumps({"messages": [
            {"role": "system", "content": "You are a helpful assistant for PowerSymphony workflows."},
            {"role": "user", "content": "How do I add a loop to my workflow?"},
            {"role": "assistant", "content": "Add a loop_counter node with max_iterations set, then connect your agent's output back to the start of the loop with an edge condition, and connect the loop_counter to continue when the limit is reached."}
        ]}),
    ]
    return {
        "ok": True,
        "example_jsonl": "\n".join(example_lines),
        "format_note": "Each line must be a JSON object with a 'messages' array containing system, user, and assistant turns."
    }
