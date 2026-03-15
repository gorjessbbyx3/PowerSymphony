"""
PowerSymphony MCP Server
========================
Exposes PowerSymphony's mission, team, workflow, and activity capabilities
as MCP tools so any AI client (Claude Code, Cursor, etc.) can connect and
collaborate with the agent team.

Usage:
  Stdio (Claude Code):
    python -m mcp_server.server

  Streamable HTTP:
    python -m mcp_server.server --transport streamable-http --port 8001
"""

from fastmcp import FastMCP
from typing import Optional
import json
import os

# ---------------------------------------------------------------------------
# Server init
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "PowerSymphony",
    instructions=(
        "You are connected to PowerSymphony — an AI team orchestration platform. "
        "You can create missions, talk to the AI team, view progress, manage workflows, "
        "and collaborate with 8 specialized AI agents. The agents self-organize: "
        "they create their own workflows, assign tasks, and share progress. "
        "Use these tools to give them goals and stay in the loop."
    ),
)

# ---------------------------------------------------------------------------
# Internal helpers — call PowerSymphony's backend
# ---------------------------------------------------------------------------

_BASE_URL = os.getenv("POWERSYMPHONY_URL", "http://localhost:8000")
_API_TOKEN = os.getenv("POWERSYMPHONY_TOKEN", "")


def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    if _API_TOKEN:
        h["Authorization"] = f"Bearer {_API_TOKEN}"
    return h


async def _api(method: str, path: str, body: dict | None = None) -> dict:
    """Make an HTTP request to the PowerSymphony backend."""
    import httpx

    url = f"{_BASE_URL}{path}"
    async with httpx.AsyncClient(timeout=30) as client:
        if method == "GET":
            resp = await client.get(url, headers=_headers())
        elif method == "POST":
            resp = await client.post(url, headers=_headers(), json=body or {})
        elif method == "PATCH":
            resp = await client.patch(url, headers=_headers(), json=body or {})
        else:
            resp = await client.request(method, url, headers=_headers(), json=body)

        if resp.status_code >= 400:
            return {"error": f"HTTP {resp.status_code}: {resp.text}"}
        try:
            return resp.json()
        except Exception:
            return {"response": resp.text}


# =========================================================================
# TOOLS — Missions
# =========================================================================

@mcp.tool
async def list_missions() -> str:
    """List all missions. Returns mission IDs, goals, and current status.
    Use this to see what the AI team is working on."""
    data = await _api("GET", "/api/missions")
    if "error" in data:
        return f"Error: {data['error']}"
    missions = data.get("missions", [])
    if not missions:
        return "No missions yet. Use create_mission to give your AI team a goal."
    lines = []
    for m in missions:
        status = m.get("status", "unknown")
        lines.append(f"- **#{m['id']}** [{status}] {m['goal']}")
    return "\n".join(lines)


@mcp.tool
async def create_mission(goal: str) -> str:
    """Create a new mission for the AI team. Describe what you want to
    build, grow, or accomplish. The team of 8 AI agents will research,
    plan, and execute it autonomously.

    Args:
        goal: What you want the AI team to accomplish (be specific).
    """
    if not goal.strip():
        return "Error: Goal cannot be empty."
    data = await _api("POST", "/api/missions", {"goal": goal.strip()})
    if "error" in data:
        return f"Error: {data['error']}"
    mid = data.get("id")
    return (
        f"Mission #{mid} created! The team is now gathering information.\n"
        f"Goal: {goal}\n\n"
        f"Use `get_mission_messages({mid})` to see the team's response, "
        f"then `send_mission_message({mid}, ...)` to answer their questions."
    )


@mcp.tool
async def get_mission(mission_id: int) -> str:
    """Get full details of a specific mission including its plan and status.

    Args:
        mission_id: The mission ID number.
    """
    data = await _api("GET", f"/api/missions/{mission_id}")
    if "error" in data:
        return f"Error: {data['error']}"
    lines = [
        f"**Mission #{data['id']}**",
        f"Goal: {data.get('goal', 'N/A')}",
        f"Status: {data.get('status', 'unknown')}",
    ]
    plan = data.get("plan")
    if plan and isinstance(plan, dict):
        lines.append(f"\n**Plan:** {plan.get('title', 'Untitled')}")
        lines.append(f"Timeline: {plan.get('timeline', 'TBD')}")
        for i, phase in enumerate(plan.get("phases", []), 1):
            lines.append(f"  {i}. {phase.get('name', 'Phase')} ({phase.get('duration', '?')})")
    return "\n".join(lines)


@mcp.tool
async def get_mission_messages(mission_id: int) -> str:
    """Get the conversation history for a mission — see what the AI agents
    have discussed, their analysis, and any questions for you.

    Args:
        mission_id: The mission ID number.
    """
    data = await _api("GET", f"/api/missions/{mission_id}/messages")
    if "error" in data:
        return f"Error: {data['error']}"
    messages = data.get("messages", [])
    if not messages:
        return "No messages yet."
    lines = []
    for m in messages[-20:]:  # Last 20 messages
        role = m.get("role", "?")
        agent = m.get("agent_name", "")
        content = m.get("content", "")
        if role == "user":
            lines.append(f"**You:** {content}")
        elif role == "agent":
            agent_info = m.get("agent", {})
            name = agent_info.get("name", agent) if agent_info else agent
            lines.append(f"**{name}:** {content}")
        else:
            lines.append(f"*[System]* {content}")
        lines.append("")
    return "\n".join(lines)


@mcp.tool
async def send_mission_message(mission_id: int, message: str) -> str:
    """Send a message to the AI team on a mission. Use this to answer
    their questions, give feedback, or provide direction.

    Special messages:
    - Say "approve", "go ahead", or "let's do it" to approve the plan
    - Say "looks good" to confirm and move to the next phase

    Args:
        mission_id: The mission ID number.
        message: Your message to the team.
    """
    if not message.strip():
        return "Error: Message cannot be empty."
    data = await _api("POST", f"/api/missions/{mission_id}/messages", {"content": message.strip()})
    if "error" in data:
        return f"Error: {data['error']}"
    return f"Message sent. Use `get_mission_messages({mission_id})` to see the team's response."


@mcp.tool
async def approve_mission_plan(mission_id: int) -> str:
    """Approve a mission's plan and start execution. Only works when the
    mission is in 'awaiting_approval' status.

    Args:
        mission_id: The mission ID number.
    """
    data = await _api("POST", f"/api/missions/{mission_id}/approve")
    if "error" in data:
        return f"Error: {data['error']}"
    return f"Plan approved! The team is now executing. Status: {data.get('status', 'executing')}"


# =========================================================================
# TOOLS — Team
# =========================================================================

@mcp.tool
async def get_team() -> str:
    """Get info about the 8 AI team members — their names, roles,
    capabilities, and KPIs."""
    data = await _api("GET", "/api/missions/team/agents")
    if "error" in data:
        return f"Error: {data['error']}"
    agents = data.get("agents", [])
    lines = []
    for a in agents:
        lines.append(f"**{a['name']}** — {a['role']}")
        lines.append(f"  {a.get('description', '')[:120]}")
        kpis = a.get("kpis", [])
        if kpis:
            lines.append(f"  KPIs: {', '.join(kpis[:2])}")
        lines.append("")
    return "\n".join(lines)


@mcp.tool
async def get_orchestration_status() -> str:
    """Get the current orchestration status — which agents are running,
    their health, and dependency graph. Shows the live state of the
    self-organizing agent system."""
    summary = await _api("GET", "/api/orchestration/summary")
    if "error" in summary:
        return f"Error: {summary['error']}"
    agents = await _api("GET", "/api/orchestration/agents")
    if "error" in agents:
        return f"Error: {agents['error']}"

    lines = [
        f"**Orchestration Summary**",
        f"Running: {summary.get('running', 0)} | Idle: {summary.get('idle', 0)} | "
        f"Health: {summary.get('health', 'unknown')}",
        "",
    ]
    for a in agents.get("agents", []):
        status = a.get("status", "idle")
        marker = "●" if status == "running" else "○"
        lines.append(f"  {marker} **{a.get('name', a.get('id', '?'))}** — {status}")
        if a.get("current_task"):
            lines.append(f"    Task: {a['current_task']}")
    return "\n".join(lines)


# =========================================================================
# TOOLS — Workflows
# =========================================================================

@mcp.tool
async def list_workflows() -> str:
    """List available workflows. Agents auto-create these to manage
    execution, but you can view and inspect them."""
    data = await _api("GET", "/api/workflows")
    if "error" in data:
        return f"Error: {data['error']}"
    workflows = data.get("workflows", data.get("files", []))
    if not workflows:
        return "No workflows yet. They'll be created automatically when agents start working."
    if isinstance(workflows[0], str):
        return "\n".join(f"- {w}" for w in workflows)
    return "\n".join(f"- {w.get('name', w.get('filename', '?'))}" for w in workflows)


@mcp.tool
async def get_workflow(name: str) -> str:
    """Get the YAML definition of a specific workflow.

    Args:
        name: Workflow filename (e.g., 'my_workflow.yaml').
    """
    data = await _api("GET", f"/api/workflows/{name}")
    if "error" in data:
        return f"Error: {data['error']}"
    content = data.get("content", "")
    if content:
        return f"```yaml\n{content}\n```"
    return json.dumps(data, indent=2)


@mcp.tool
async def execute_workflow(yaml_file: str, task_prompt: str) -> str:
    """Execute a workflow with a task prompt. The agents will run the
    workflow and report progress.

    Args:
        yaml_file: Workflow filename to execute.
        task_prompt: The task/prompt to feed into the workflow.
    """
    data = await _api("POST", "/api/workflow/execute", {
        "yaml_file": yaml_file,
        "task_prompt": task_prompt,
    })
    if "error" in data:
        return f"Error: {data['error']}"
    session_id = data.get("session_id", "unknown")
    return f"Workflow started! Session: {session_id}\nUse `get_session_status('{session_id}')` to check progress."


# =========================================================================
# TOOLS — Sessions & Activity
# =========================================================================

@mcp.tool
async def list_sessions() -> str:
    """List active and recent workflow sessions — shows what's running
    and what's completed."""
    data = await _api("GET", "/api/sessions")
    if "error" in data:
        return f"Error: {data['error']}"
    sessions = data.get("sessions", [])
    if not sessions:
        return "No sessions."
    lines = []
    for s in sessions[:15]:
        sid = s.get("session_id", s.get("id", "?"))
        status = s.get("status", "unknown")
        lines.append(f"- **{sid}** [{status}]")
    return "\n".join(lines)


@mcp.tool
async def get_session_status(session_id: str) -> str:
    """Get the status and results of a workflow execution session.

    Args:
        session_id: The session ID returned from execute_workflow.
    """
    data = await _api("GET", f"/api/sessions/{session_id}/artifact-events?limit=5")
    if "error" in data:
        return f"Error: {data['error']}"
    events = data.get("events", [])
    if not events:
        return f"Session {session_id}: No events yet (may still be starting)."
    lines = [f"**Session {session_id}** — Recent events:"]
    for e in events:
        lines.append(f"- {e.get('type', '?')}: {e.get('data', {}).get('name', 'unnamed')}")
    return "\n".join(lines)


# =========================================================================
# TOOLS — System
# =========================================================================

@mcp.tool
async def get_system_health() -> str:
    """Check the PowerSymphony system health and readiness."""
    health = await _api("GET", "/health/ready")
    if "error" in health:
        return f"System may be down: {health['error']}"
    return f"System status: {health.get('status', 'unknown')}"


# =========================================================================
# Resources — provide context to the AI
# =========================================================================

@mcp.resource("powersymphony://team")
async def team_resource() -> str:
    """The PowerSymphony AI team roster and capabilities."""
    return await get_team()


@mcp.resource("powersymphony://missions")
async def missions_resource() -> str:
    """Current missions and their statuses."""
    return await list_missions()


# =========================================================================
# Entrypoint
# =========================================================================

if __name__ == "__main__":
    import sys

    transport = "stdio"
    port = 8001

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--transport" and i + 1 < len(args):
            transport = args[i + 1]
            i += 2
        elif args[i] == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
        else:
            i += 1

    if transport == "streamable-http":
        mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
    else:
        mcp.run(transport="stdio")
