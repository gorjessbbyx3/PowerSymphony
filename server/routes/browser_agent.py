"""Browser agent WebSocket endpoint — bridges AI workers with the Chrome extension."""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()

# session_id -> WebSocket for connected browser extensions
_browser_sessions: Dict[str, WebSocket] = {}
# Pending command futures: command_id -> asyncio.Future
_pending_commands: Dict[str, asyncio.Future] = {}


@router.websocket("/ws/browser-agent")
async def browser_agent_endpoint(websocket: WebSocket):
    """WebSocket endpoint that browser extensions connect to."""
    await websocket.accept()
    session_id: Optional[str] = None

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "error": "Invalid JSON"}))
                continue

            msg_type = msg.get("type")

            if msg_type == "browser_agent_register":
                session_id = msg.get("session_id") or str(id(websocket))
                _browser_sessions[session_id] = websocket
                logger.info(f"Browser agent registered: {session_id}")
                await websocket.send_text(json.dumps({
                    "type": "registered",
                    "session_id": session_id,
                }))

            elif msg_type == "command_result":
                command_id = msg.get("command_id")
                fut = _pending_commands.pop(command_id, None)
                if fut and not fut.done():
                    error = msg.get("error")
                    if error:
                        fut.set_exception(RuntimeError(error))
                    else:
                        fut.set_result(msg.get("result"))

            elif msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "session_id": session_id}))

    except WebSocketDisconnect:
        logger.info(f"Browser agent disconnected: {session_id}")
    finally:
        if session_id and session_id in _browser_sessions:
            del _browser_sessions[session_id]


async def send_browser_command(
    command: str,
    params: Dict[str, Any],
    session_id: Optional[str] = None,
    timeout: float = 30.0,
) -> Any:
    """
    Send a command to a connected browser extension and await the result.

    Args:
        command: Command type (e.g. 'click', 'type', 'screenshot', 'navigate')
        params: Command parameters (selector, text, url, etc.)
        session_id: Target browser session (uses first available if None)
        timeout: Seconds to wait for result

    Returns:
        Command result from the browser extension

    Raises:
        RuntimeError if no browser is connected or command times out
    """
    if not _browser_sessions:
        raise RuntimeError("No browser extension connected. Install and connect the PowerSymphony extension.")

    ws = _browser_sessions.get(session_id) if session_id else next(iter(_browser_sessions.values()))
    if not ws:
        raise RuntimeError(f"Browser session not found: {session_id}")

    import uuid
    command_id = str(uuid.uuid4())
    fut: asyncio.Future = asyncio.get_event_loop().create_future()
    _pending_commands[command_id] = fut

    msg = {"type": command, "command_id": command_id, **params}
    await ws.send_text(json.dumps(msg))

    try:
        return await asyncio.wait_for(fut, timeout=timeout)
    except asyncio.TimeoutError:
        _pending_commands.pop(command_id, None)
        raise RuntimeError(f"Browser command '{command}' timed out after {timeout}s")


def get_connected_sessions() -> list:
    """Return list of connected browser session IDs."""
    return list(_browser_sessions.keys())
