from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from server.services import mission_service

router = APIRouter(prefix="/api/missions", tags=["missions"])


class CreateMissionRequest(BaseModel):
    goal: str


class SendMessageRequest(BaseModel):
    content: str


def _get_user_id(request: Request) -> int:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user["id"]


@router.get("/team/agents")
async def get_team_agents(request: Request):
    return {"agents": mission_service.TEAM_AGENTS}


@router.post("")
async def create_mission(req: CreateMissionRequest, request: Request):
    user_id = _get_user_id(request)
    if not req.goal.strip():
        raise HTTPException(status_code=400, detail="Goal cannot be empty")
    mission = mission_service.create_mission(user_id, req.goal.strip())
    return mission


@router.get("")
async def list_missions(request: Request):
    user_id = _get_user_id(request)
    missions = mission_service.list_missions(user_id)
    return {"missions": missions}


@router.get("/{mission_id}")
async def get_mission(mission_id: int, request: Request):
    user_id = _get_user_id(request)
    mission = mission_service.get_mission(mission_id, user_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


@router.get("/{mission_id}/messages")
async def get_messages(mission_id: int, request: Request):
    user_id = _get_user_id(request)
    messages = mission_service.get_messages(mission_id, user_id)
    if messages is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return {"messages": messages}


@router.post("/{mission_id}/messages")
async def send_message(mission_id: int, req: SendMessageRequest, request: Request):
    user_id = _get_user_id(request)
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    try:
        result = mission_service.send_message(mission_id, user_id, req.content.strip())
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{mission_id}/approve")
async def approve_plan(mission_id: int, request: Request):
    user_id = _get_user_id(request)
    try:
        result = mission_service.approve_plan(mission_id, user_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{mission_id}/votes")
async def get_votes(mission_id: int, request: Request):
    _get_user_id(request)
    votes = mission_service.get_votes(mission_id)
    return {"votes": votes}
