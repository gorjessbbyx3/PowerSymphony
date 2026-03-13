"""Aggregates API routers."""

from . import artifacts, batch, browser_agent, browser_control, execute, health, sessions, uploads, vuegraphs, workflows, websocket

ALL_ROUTERS = [
    health.router,
    vuegraphs.router,
    workflows.router,
    uploads.router,
    artifacts.router,
    sessions.router,
    batch.router,
    execute.router,
    websocket.router,
    browser_agent.router,
    browser_control.router,
]

__all__ = ["ALL_ROUTERS"]
