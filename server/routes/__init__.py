"""Aggregates API routers."""

from . import (
    artifacts, batch, browser_agent, browser_control, cloud_deploy,
    crm, execute, health, scraping, sessions, system_stats,
    uploads, vuegraphs, workflows, websocket,
)

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
    system_stats.router,
    scraping.router,
    crm.router,
    cloud_deploy.router,
]

__all__ = ["ALL_ROUTERS"]
