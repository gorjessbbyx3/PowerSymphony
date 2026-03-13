"""Orchestration Dashboard — 8-agent management, KPIs, dependencies, sync log."""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/orchestration", tags=["orchestration"])

_ORCH_DIR = Path("WareHouse/.orchestration")
_ORCH_DIR.mkdir(parents=True, exist_ok=True)
_SYNC_LOG = _ORCH_DIR / "sync_log.jsonl"
_STATUS_FILE = _ORCH_DIR / "agent_status.json"

AGENTS = [
    {
        "id": "market_researcher",
        "name": "Market Researcher",
        "icon": "search",
        "color": "#4ecdc4",
        "kpi": "50 validated pain points/week",
        "kpi_metric": "pain_points_validated",
        "kpi_target": 50,
        "kpi_unit": "/week",
        "description": "Analyzes sales data, identifies target industries (SaaS 50-500 employees), validates pain points with evidence.",
        "yaml_file": "yaml_instance/orchestration/market_researcher.yaml",
        "sub_agents": ["Industry Scanner", "Pain Point Validator", "Competitor Analyst", "Research Synthesizer"],
        "depends_on": [],
        "feeds_into": ["product_strategist", "sales_marketing", "fundraising_ops"],
    },
    {
        "id": "product_strategist",
        "name": "Product Strategist",
        "icon": "lightbulb",
        "color": "#a78bfa",
        "kpi": "Quarterly roadmap with user feedback updates",
        "kpi_metric": "roadmap_features_defined",
        "kpi_target": 20,
        "kpi_unit": "/quarter",
        "description": "Defines features via RICE scoring, maintains quarterly roadmap driven by user feedback loops.",
        "yaml_file": "yaml_instance/orchestration/product_strategist.yaml",
        "sub_agents": ["Feedback Collector", "Feature Prioritizer", "Roadmap Architect", "Spec Writer"],
        "depends_on": ["market_researcher", "sales_marketing", "tester_compliance", "scaler_innovator", "fundraising_ops"],
        "feeds_into": ["core_engineer", "integration_engineer", "tester_compliance"],
    },
    {
        "id": "core_engineer",
        "name": "Core Engineer",
        "icon": "code",
        "color": "#f472b6",
        "kpi": "Deploy MVP backend in 4 weeks",
        "kpi_metric": "features_shipped",
        "kpi_target": 12,
        "kpi_unit": "/month",
        "description": "Builds orchestration engine, agent communication protocols, RLHF self-improvement module.",
        "yaml_file": "yaml_instance/orchestration/core_engineer.yaml",
        "sub_agents": ["Architecture Planner", "Backend Developer", "Frontend Developer", "Code Reviewer"],
        "depends_on": ["product_strategist", "tester_compliance", "scaler_innovator"],
        "feeds_into": ["tester_compliance", "integration_engineer", "scaler_innovator"],
    },
    {
        "id": "integration_engineer",
        "name": "Integration Engineer",
        "icon": "plug",
        "color": "#fbbf24",
        "kpi": "95% uptime, 5+ integrations by launch",
        "kpi_metric": "integrations_live",
        "kpi_target": 5,
        "kpi_unit": " total",
        "description": "Handles API hooks to HubSpot, GitHub, Slack, cloud providers. Monitors integration health.",
        "yaml_file": "yaml_instance/orchestration/integration_engineer.yaml",
        "sub_agents": ["Integration Planner", "API Builder", "Health Monitor"],
        "depends_on": ["product_strategist", "core_engineer"],
        "feeds_into": ["tester_compliance", "scaler_innovator"],
    },
    {
        "id": "tester_compliance",
        "name": "Tester & Compliance",
        "icon": "shield",
        "color": "#34d399",
        "kpi": "Zero critical bugs; GDPR compliance",
        "kpi_metric": "critical_bugs",
        "kpi_target": 0,
        "kpi_unit": " bugs",
        "description": "Simulates workflows, runs automated tests, ensures ethical AI (bias checks), GDPR compliance.",
        "yaml_file": "yaml_instance/orchestration/tester_compliance.yaml",
        "sub_agents": ["Test Planner", "Automated Tester", "Bias Auditor", "QA Reporter"],
        "depends_on": ["core_engineer", "integration_engineer"],
        "feeds_into": ["core_engineer", "product_strategist"],
    },
    {
        "id": "sales_marketing",
        "name": "Sales & Marketing",
        "icon": "megaphone",
        "color": "#fb923c",
        "kpi": "20 beta users in Month 2",
        "kpi_metric": "beta_users_acquired",
        "kpi_target": 20,
        "kpi_unit": " users",
        "description": "Crafts pitches, runs A/B tests, manages LinkedIn/email campaigns for beta user acquisition.",
        "yaml_file": "yaml_instance/orchestration/sales_marketing.yaml",
        "sub_agents": ["Persona Builder", "Content Engine", "Campaign Optimizer"],
        "depends_on": ["market_researcher", "product_strategist"],
        "feeds_into": ["fundraising_ops", "product_strategist"],
    },
    {
        "id": "fundraising_ops",
        "name": "Fundraising & Ops",
        "icon": "dollar",
        "color": "#60a5fa",
        "kpi": "Secure $1M angel funding (Month 3); CAC:LTV > 1:3",
        "kpi_metric": "funding_secured_k",
        "kpi_target": 1000,
        "kpi_unit": "K",
        "description": "Models financials, generates pitch decks, monitors CAC:LTV ratio and operational metrics.",
        "yaml_file": "yaml_instance/orchestration/fundraising_ops.yaml",
        "sub_agents": ["Financial Modeler", "Pitch Deck Generator", "Metrics Monitor"],
        "depends_on": ["market_researcher", "sales_marketing"],
        "feeds_into": ["scaler_innovator", "product_strategist"],
    },
    {
        "id": "scaler_innovator",
        "name": "Scaler & Innovator",
        "icon": "rocket",
        "color": "#e879f9",
        "kpi": "Reduce workflow time by 20% quarterly",
        "kpi_metric": "workflow_time_reduction_pct",
        "kpi_target": 20,
        "kpi_unit": "%",
        "description": "Optimizes performance, implements auto-scaling, prototypes innovations like voice-enabled deal closing.",
        "yaml_file": "yaml_instance/orchestration/scaler_innovator.yaml",
        "sub_agents": ["Performance Profiler", "Auto-Scaler", "Innovation Lab", "Optimization Executor"],
        "depends_on": ["core_engineer", "integration_engineer", "fundraising_ops"],
        "feeds_into": ["core_engineer", "product_strategist"],
    },
]

AGENT_MAP = {a["id"]: a for a in AGENTS}


def _load_status() -> Dict[str, Any]:
    if _STATUS_FILE.exists():
        try:
            return json.loads(_STATUS_FILE.read_text())
        except Exception:
            pass
    defaults = {}
    for a in AGENTS:
        defaults[a["id"]] = {
            "status": "idle",
            "kpi_current": 0,
            "last_run": None,
            "runs_total": 0,
            "health": "healthy",
        }
    return defaults


def _save_status(data: Dict[str, Any]) -> None:
    _STATUS_FILE.write_text(json.dumps(data, indent=2))


def _append_sync(entry: Dict[str, Any]) -> None:
    entry.setdefault("timestamp", time.time())
    with open(_SYNC_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _load_sync_log(limit: int = 50) -> List[Dict[str, Any]]:
    if not _SYNC_LOG.exists():
        return []
    lines = _SYNC_LOG.read_text().strip().splitlines()
    entries = []
    for line in reversed(lines):
        if line.strip():
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
        if len(entries) >= limit:
            break
    return entries


@router.get("/agents")
async def list_agents() -> Dict[str, Any]:
    status = _load_status()
    agents_out = []
    for a in AGENTS:
        s = status.get(a["id"], {})
        agents_out.append({
            **a,
            "status": s.get("status", "idle"),
            "kpi_current": s.get("kpi_current", 0),
            "last_run": s.get("last_run"),
            "runs_total": s.get("runs_total", 0),
            "health": s.get("health", "healthy"),
        })
    return {"ok": True, "agents": agents_out}


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str) -> Dict[str, Any]:
    if agent_id not in AGENT_MAP:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    status = _load_status()
    s = status.get(agent_id, {})
    return {"ok": True, "agent": {**AGENT_MAP[agent_id], **s}}


class StatusUpdate(BaseModel):
    status: Optional[str] = None
    kpi_current: Optional[float] = None
    health: Optional[str] = None


@router.patch("/agents/{agent_id}")
async def update_agent_status(agent_id: str, body: StatusUpdate) -> Dict[str, Any]:
    if agent_id not in AGENT_MAP:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    status = _load_status()
    s = status.setdefault(agent_id, {"status": "idle", "kpi_current": 0, "last_run": None, "runs_total": 0, "health": "healthy"})
    if body.status is not None:
        s["status"] = body.status
    if body.kpi_current is not None:
        s["kpi_current"] = body.kpi_current
    if body.health is not None:
        s["health"] = body.health
    _save_status(status)
    _append_sync({"type": "status_update", "agent_id": agent_id, "updates": body.dict(exclude_none=True)})
    return {"ok": True, "agent": {**AGENT_MAP[agent_id], **s}}


class RunRecord(BaseModel):
    agent_id: str


@router.post("/agents/{agent_id}/run")
async def record_run(agent_id: str) -> Dict[str, Any]:
    if agent_id not in AGENT_MAP:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    status = _load_status()
    s = status.setdefault(agent_id, {"status": "idle", "kpi_current": 0, "last_run": None, "runs_total": 0, "health": "healthy"})
    s["status"] = "running"
    s["last_run"] = time.time()
    s["runs_total"] = s.get("runs_total", 0) + 1
    _save_status(status)
    _append_sync({"type": "run_started", "agent_id": agent_id})
    return {"ok": True, "agent": {**AGENT_MAP[agent_id], **s}}


@router.post("/agents/{agent_id}/complete")
async def complete_run(agent_id: str) -> Dict[str, Any]:
    if agent_id not in AGENT_MAP:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    status = _load_status()
    s = status.setdefault(agent_id, {"status": "idle", "kpi_current": 0, "last_run": None, "runs_total": 0, "health": "healthy"})
    s["status"] = "idle"
    _save_status(status)
    _append_sync({"type": "run_completed", "agent_id": agent_id})
    return {"ok": True, "agent": {**AGENT_MAP[agent_id], **s}}


@router.get("/dependencies")
async def get_dependency_graph() -> Dict[str, Any]:
    nodes = []
    edges = []
    for a in AGENTS:
        nodes.append({"id": a["id"], "label": a["name"], "color": a["color"]})
        for dep in a["feeds_into"]:
            edges.append({"from": a["id"], "to": dep})
    return {"ok": True, "nodes": nodes, "edges": edges}


class SyncEntry(BaseModel):
    agent_id: str
    message: str
    sync_type: str = "update"


@router.post("/sync")
async def add_sync_entry(body: SyncEntry) -> Dict[str, Any]:
    if body.agent_id not in AGENT_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown agent_id '{body.agent_id}'")
    entry = {
        "type": body.sync_type,
        "agent_id": body.agent_id,
        "message": body.message,
        "timestamp": time.time(),
    }
    _append_sync(entry)
    return {"ok": True, "entry": entry}


@router.get("/sync")
async def get_sync_log(limit: int = 50) -> Dict[str, Any]:
    clamped = max(1, min(limit, 200))
    entries = _load_sync_log(clamped)
    return {"ok": True, "entries": entries}


@router.get("/kpis")
async def get_kpis() -> Dict[str, Any]:
    status = _load_status()
    kpis = []
    for a in AGENTS:
        s = status.get(a["id"], {})
        current = s.get("kpi_current", 0)
        target = a["kpi_target"]
        progress = min(100, (current / target * 100)) if target > 0 else 0
        kpis.append({
            "agent_id": a["id"],
            "agent_name": a["name"],
            "kpi": a["kpi"],
            "metric": a["kpi_metric"],
            "current": current,
            "target": target,
            "unit": a["kpi_unit"],
            "progress_pct": round(progress, 1),
            "color": a["color"],
        })
    return {"ok": True, "kpis": kpis}


@router.get("/summary")
async def get_summary() -> Dict[str, Any]:
    status = _load_status()
    total_runs = sum(s.get("runs_total", 0) for s in status.values())
    running = sum(1 for s in status.values() if s.get("status") == "running")
    healthy = sum(1 for s in status.values() if s.get("health") == "healthy")
    kpis_met = 0
    for a in AGENTS:
        s = status.get(a["id"], {})
        current = s.get("kpi_current", 0)
        if a["kpi_target"] > 0 and current >= a["kpi_target"]:
            kpis_met += 1
        elif a["kpi_target"] == 0 and current == 0:
            kpis_met += 1
    return {
        "ok": True,
        "total_agents": len(AGENTS),
        "agents_running": running,
        "agents_healthy": healthy,
        "total_runs": total_runs,
        "kpis_met": kpis_met,
        "kpis_total": len(AGENTS),
    }
