"""Aggregates API routers."""

from . import (
    agent_performance, artifacts, auth, batch, browser_agent, browser_control,
    cicd, cloud_deploy, collaboration, crm, diagrams, execute, fine_tuning,
    github_copilot, health, marketplace, orchestration, scraping, sessions,
    system_stats, uploads, vuegraphs, workflows, websocket,
)

ALL_ROUTERS = [
    health.router,
    auth.router,
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
    agent_performance.router,
    github_copilot.router,
    cicd.router,
    fine_tuning.router,
    marketplace.router,
    collaboration.router,
    diagrams.router,
    orchestration.router,
]

__all__ = ["ALL_ROUTERS"]
