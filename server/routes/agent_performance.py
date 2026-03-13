"""REST API for agent performance tracking and self-improvement."""

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/performance", tags=["agent_performance"])


class ScoreRequest(BaseModel):
    task: str
    output: str
    criteria: str = ""


class RefineRequest(BaseModel):
    task: str
    initial_output: str
    max_iterations: int = 3
    score_threshold: float = 8.0


class PromptImprovementRequest(BaseModel):
    current_role: str
    task_examples: str
    critique_examples: str


class SaveRunRequest(BaseModel):
    task: str
    output: str
    score: float
    critique: str = ""
    strengths: str = ""
    prompt_version: int = 0


@router.get("")
async def list_agents() -> Dict[str, Any]:
    """List all agents that have performance data on disk."""
    try:
        from utils.agent_performance_store import list_all_agents
        agents = list_all_agents()
        return {"ok": True, "agents": agents, "count": len(agents)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{agent_id}")
async def agent_stats(agent_id: str) -> Dict[str, Any]:
    """Get aggregate stats and performance trend for an agent."""
    try:
        from utils.agent_performance_store import get_store
        store = get_store(agent_id)
        stats = store.get_stats()
        trend = store.get_performance_trend(n=10)
        return {"ok": True, "stats": stats, "trend": trend}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{agent_id}/runs")
async def agent_runs(agent_id: str, n: int = 10) -> Dict[str, Any]:
    """Return recent scored runs for an agent."""
    try:
        from utils.agent_performance_store import get_store
        store = get_store(agent_id)
        runs = store.get_recent_runs(n=min(n, 100))
        return {"ok": True, "runs": [r.to_dict() for r in runs], "count": len(runs)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{agent_id}/prompt")
async def best_prompt(agent_id: str) -> Dict[str, Any]:
    """Return the best-performing evolved prompt for an agent."""
    try:
        from utils.agent_performance_store import get_store
        store = get_store(agent_id)
        best = store.get_best_prompt()
        current = store.get_current_prompt()
        versions = store.get_all_prompt_versions()
        return {
            "ok": True,
            "agent_id": agent_id,
            "best_prompt": best,
            "current_prompt": current,
            "versions": versions,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{agent_id}/score")
async def score_output(agent_id: str, req: ScoreRequest) -> Dict[str, Any]:
    """Score an agent's output using an LLM judge."""
    try:
        from functions.function_calling.self_improve import score_my_output
        result = json.loads(score_my_output(req.task, req.output, criteria=req.criteria))
        return {"ok": True, "agent_id": agent_id, **result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{agent_id}/refine")
async def refine_output(agent_id: str, req: RefineRequest) -> Dict[str, Any]:
    """Iteratively refine an output until it reaches a quality threshold."""
    try:
        from functions.function_calling.self_improve import run_iterative_refinement
        result = json.loads(run_iterative_refinement(
            req.task, req.initial_output,
            max_iterations=req.max_iterations,
            score_threshold=req.score_threshold,
        ))
        return {"ok": True, "agent_id": agent_id, **result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{agent_id}/improve-prompt")
async def improve_prompt(agent_id: str, req: PromptImprovementRequest) -> Dict[str, Any]:
    """Generate and save an improved prompt for an agent."""
    try:
        from functions.function_calling.self_improve import improve_my_prompt
        result = json.loads(improve_my_prompt(
            agent_id, req.current_role,
            req.task_examples, req.critique_examples,
        ))
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return {"ok": True, **result}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{agent_id}/runs")
async def save_run(agent_id: str, req: SaveRunRequest) -> Dict[str, Any]:
    """Manually save a run record for an agent."""
    try:
        from functions.function_calling.self_improve import save_performance
        result = json.loads(save_performance(
            agent_id, req.task, req.output, req.score,
            critique=req.critique, strengths=req.strengths,
            prompt_version=req.prompt_version,
        ))
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{agent_id}")
async def reset_agent(agent_id: str) -> Dict[str, Any]:
    """Reset (wipe) all performance data for an agent."""
    try:
        from utils.agent_performance_store import get_store
        store = get_store(agent_id)
        store.reset()
        return {"ok": True, "agent_id": agent_id, "message": "Performance data cleared."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
