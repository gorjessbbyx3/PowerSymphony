"""Real-Time Collaboration — WebSocket rooms for shared agent prompting sessions."""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

router = APIRouter(prefix="/api/collab", tags=["collaboration"])


class Room:
    def __init__(self, room_id: str, name: str, description: str, owner: str):
        self.room_id = room_id
        self.name = name
        self.description = description
        self.owner = owner
        self.created_at = int(time.time())
        self.connections: Dict[str, WebSocket] = {}
        self.history: List[Dict] = []
        self.shared_prompt: str = ""

    def to_dict(self) -> Dict:
        return {
            "room_id": self.room_id,
            "name": self.name,
            "description": self.description,
            "owner": self.owner,
            "created_at": self.created_at,
            "active_users": list(self.connections.keys()),
            "user_count": len(self.connections),
            "history_length": len(self.history),
            "shared_prompt": self.shared_prompt,
        }

    async def broadcast(self, message: Dict, exclude: Optional[str] = None):
        message["timestamp"] = int(time.time() * 1000)
        dead = []
        for user_id, ws in self.connections.items():
            if user_id == exclude:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(user_id)
        for user_id in dead:
            self.connections.pop(user_id, None)


_rooms: Dict[str, Room] = {}


class CreateRoomRequest(BaseModel):
    name: str
    description: str = ""
    owner: str = "anonymous"


class UpdatePromptRequest(BaseModel):
    prompt: str
    user_id: str


@router.get("/rooms")
async def list_rooms() -> Dict[str, Any]:
    """List all active collaboration rooms."""
    return {
        "ok": True,
        "rooms": [r.to_dict() for r in _rooms.values()],
        "count": len(_rooms),
    }


@router.post("/rooms")
async def create_room(req: CreateRoomRequest) -> Dict[str, Any]:
    """Create a new collaboration room."""
    room_id = uuid.uuid4().hex[:8]
    room = Room(room_id=room_id, name=req.name, description=req.description, owner=req.owner)
    _rooms[room_id] = room
    return {"ok": True, "room": room.to_dict()}


@router.get("/rooms/{room_id}")
async def get_room(room_id: str) -> Dict[str, Any]:
    """Get details for a specific room."""
    if room_id not in _rooms:
        raise HTTPException(status_code=404, detail=f"Room '{room_id}' not found.")
    return {"ok": True, "room": _rooms[room_id].to_dict()}


@router.delete("/rooms/{room_id}")
async def delete_room(room_id: str) -> Dict[str, Any]:
    """Delete a collaboration room and disconnect all users."""
    if room_id not in _rooms:
        raise HTTPException(status_code=404, detail=f"Room '{room_id}' not found.")
    room = _rooms.pop(room_id)
    await room.broadcast({"type": "room_closed", "message": "This room has been closed."})
    return {"ok": True, "message": f"Room '{room.name}' deleted."}


@router.get("/rooms/{room_id}/history")
async def get_history(room_id: str, limit: int = 50) -> Dict[str, Any]:
    """Get message history for a room."""
    if room_id not in _rooms:
        raise HTTPException(status_code=404, detail=f"Room '{room_id}' not found.")
    history = _rooms[room_id].history[-limit:]
    return {"ok": True, "history": history, "count": len(history)}


@router.post("/rooms/{room_id}/prompt")
async def update_shared_prompt(room_id: str, req: UpdatePromptRequest) -> Dict[str, Any]:
    """Update the shared prompt in a room and broadcast the change."""
    if room_id not in _rooms:
        raise HTTPException(status_code=404, detail=f"Room '{room_id}' not found.")
    room = _rooms[room_id]
    room.shared_prompt = req.prompt
    msg = {"type": "prompt_updated", "user_id": req.user_id, "prompt": req.prompt}
    room.history.append(msg)
    if len(room.history) > 200:
        room.history = room.history[-200:]
    await room.broadcast(msg, exclude=req.user_id)
    return {"ok": True, "prompt": req.prompt}


@router.websocket("/rooms/{room_id}/ws")
async def room_websocket(websocket: WebSocket, room_id: str, user_id: str = ""):
    """WebSocket endpoint for joining a collaboration room."""
    if room_id not in _rooms:
        await websocket.close(code=4004, reason=f"Room '{room_id}' not found.")
        return

    room = _rooms[room_id]
    if not user_id:
        user_id = f"user-{uuid.uuid4().hex[:6]}"

    await websocket.accept()
    room.connections[user_id] = websocket

    join_msg = {"type": "user_joined", "user_id": user_id, "active_users": list(room.connections.keys())}
    room.history.append(join_msg)
    await room.broadcast(join_msg)
    await websocket.send_json({"type": "welcome", "user_id": user_id,
                                "room": room.to_dict(), "history": room.history[-20:]})

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "message")

            if msg_type == "message":
                msg = {"type": "message", "user_id": user_id, "text": data.get("text", ""), "timestamp": int(time.time() * 1000)}
                room.history.append(msg)
                if len(room.history) > 200:
                    room.history = room.history[-200:]
                await room.broadcast(msg)

            elif msg_type == "prompt_update":
                room.shared_prompt = data.get("prompt", "")
                msg = {"type": "prompt_updated", "user_id": user_id, "prompt": room.shared_prompt}
                room.history.append(msg)
                await room.broadcast(msg, exclude=user_id)

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong", "user_id": user_id})

    except WebSocketDisconnect:
        pass
    finally:
        room.connections.pop(user_id, None)
        leave_msg = {"type": "user_left", "user_id": user_id, "active_users": list(room.connections.keys())}
        room.history.append(leave_msg)
        await room.broadcast(leave_msg)
