"""System performance stats and diagnostics API."""

import os
import platform
import time
from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """Return runtime performance statistics."""
    stats: Dict[str, Any] = {
        "timestamp": time.time(),
        "python": platform.python_version(),
        "platform": platform.system(),
    }

    # LLM cache stats
    try:
        from utils.llm_cache import llm_cache
        stats["llm_cache"] = llm_cache.stats
    except Exception as exc:
        stats["llm_cache"] = {"error": str(exc)}

    # Session counts
    try:
        from server.state import get_websocket_manager
        manager = get_websocket_manager()
        store = manager.session_store
        sessions = store.list_sessions()
        historical = store.load_historical_sessions()
        stats["sessions"] = {
            "active": len(sessions),
            "historical": len(historical),
            "by_status": _count_by_status(sessions),
        }
    except Exception as exc:
        stats["sessions"] = {"error": str(exc)}

    # Browser extension connections
    try:
        from server.routes.browser_agent import get_connected_sessions
        stats["browser_sessions"] = len(get_connected_sessions())
    except Exception as exc:
        stats["browser_sessions"] = 0

    # Provider registry
    try:
        from runtime.node.agent.providers.base import ProviderRegistry
        stats["providers"] = ProviderRegistry.list_providers()
    except Exception as exc:
        stats["providers"] = []

    # Env info (safe subset)
    stats["config"] = {
        "llm_cache_enabled": os.environ.get("POWERSYMPHONY_LLM_CACHE", "true"),
        "max_parallel_tools": os.environ.get("POWERSYMPHONY_MAX_PARALLEL_TOOLS", "8"),
        "llm_cache_max_entries": os.environ.get("LLM_CACHE_MAX_ENTRIES", "512"),
    }

    return stats


@router.post("/cache/clear")
async def clear_llm_cache() -> Dict[str, Any]:
    """Clear the in-memory LLM response cache."""
    try:
        from utils.llm_cache import llm_cache
        before = llm_cache.stats["entries"]
        llm_cache.clear()
        return {"ok": True, "cleared_entries": before}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/health/detailed")
async def detailed_health() -> Dict[str, Any]:
    """Extended health check with component status."""
    checks: Dict[str, Any] = {}

    # Backend server
    checks["server"] = "ok"

    # LLM cache
    try:
        from utils.llm_cache import llm_cache
        _ = llm_cache.stats
        checks["llm_cache"] = "ok"
    except Exception as exc:
        checks["llm_cache"] = f"error: {exc}"

    # Provider registry
    try:
        from runtime.node.agent.providers.base import ProviderRegistry
        providers = ProviderRegistry.list_providers()
        checks["providers"] = {"status": "ok", "available": providers}
    except Exception as exc:
        checks["providers"] = {"status": "error", "error": str(exc)}

    # YAML workflow files
    try:
        from pathlib import Path
        yaml_count = len(list(Path("yaml_instance").glob("*.yaml")))
        checks["workflows"] = {"status": "ok", "count": yaml_count}
    except Exception as exc:
        checks["workflows"] = {"status": "error", "error": str(exc)}

    all_ok = all(
        (v == "ok" or (isinstance(v, dict) and v.get("status") == "ok"))
        for v in checks.values()
    )

    return {"status": "ok" if all_ok else "degraded", "checks": checks}


def _count_by_status(sessions: Dict[str, Any]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for info in sessions.values():
        s = info.get("status", "unknown") if info else "unknown"
        counts[s] = counts.get(s, 0) + 1
    return counts
