"""REST API for CRM (HubSpot) integration."""

import json
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/crm", tags=["crm"])


class ContactCreateRequest(BaseModel):
    email: str
    firstname: str = ""
    lastname: str = ""
    extra_properties: Dict[str, Any] = {}


class ContactUpdateRequest(BaseModel):
    properties: Dict[str, Any]


class DealCreateRequest(BaseModel):
    dealname: str
    amount: float = 0
    stage: str = "appointmentscheduled"
    pipeline: str = "default"
    contact_id: str = ""


class ActivityRequest(BaseModel):
    subject: str
    body: str
    activity_type: str = "NOTE"


@router.get("/status")
async def crm_status() -> Dict[str, Any]:
    """Check if the HubSpot API key is configured."""
    has_key = bool(
        os.environ.get("HUBSPOT_API_KEY") or os.environ.get("HUBSPOT_ACCESS_TOKEN")
    )
    return {
        "provider": "hubspot",
        "configured": has_key,
        "hint": "Set HUBSPOT_API_KEY or HUBSPOT_ACCESS_TOKEN in your environment." if not has_key else None,
    }


@router.get("/contacts/search")
async def search_contacts(q: str, limit: int = 10) -> Dict[str, Any]:
    """Search contacts by name or email."""
    try:
        from functions.function_calling.crm import crm_search_contacts
        result = crm_search_contacts(q, limit=limit)
        return {"ok": True, "contacts": json.loads(result)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/contacts")
async def create_contact(req: ContactCreateRequest) -> Dict[str, Any]:
    """Create a new HubSpot contact."""
    try:
        from functions.function_calling.crm import crm_create_contact
        result = crm_create_contact(
            req.email,
            firstname=req.firstname,
            lastname=req.lastname,
            extra_properties=json.dumps(req.extra_properties),
        )
        data = json.loads(result)
        if "error" in data:
            raise HTTPException(status_code=400, detail=data["error"])
        return {"ok": True, "contact": data}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.patch("/contacts/{contact_id}")
async def update_contact(contact_id: str, req: ContactUpdateRequest) -> Dict[str, Any]:
    """Update an existing HubSpot contact."""
    try:
        from functions.function_calling.crm import crm_update_contact
        result = crm_update_contact(contact_id, properties=json.dumps(req.properties))
        data = json.loads(result)
        if "error" in data:
            raise HTTPException(status_code=400, detail=data["error"])
        return {"ok": True, "contact": data}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/deals")
async def list_deals(limit: int = 10, pipeline: str = "") -> Dict[str, Any]:
    """List deals from HubSpot CRM."""
    try:
        from functions.function_calling.crm import crm_list_deals
        result = crm_list_deals(limit=limit, pipeline=pipeline)
        return {"ok": True, "deals": json.loads(result)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/deals")
async def create_deal(req: DealCreateRequest) -> Dict[str, Any]:
    """Create a new HubSpot deal."""
    try:
        from functions.function_calling.crm import crm_create_deal
        result = crm_create_deal(
            req.dealname, amount=req.amount, stage=req.stage,
            pipeline=req.pipeline, contact_id=req.contact_id,
        )
        data = json.loads(result)
        if "error" in data:
            raise HTTPException(status_code=400, detail=data["error"])
        return {"ok": True, "deal": data}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/contacts/{contact_id}/activities")
async def log_activity(contact_id: str, req: ActivityRequest) -> Dict[str, Any]:
    """Log an activity (note, call, or email) against a HubSpot contact."""
    try:
        from functions.function_calling.crm import crm_log_activity
        result = crm_log_activity(
            contact_id, subject=req.subject, body=req.body,
            activity_type=req.activity_type,
        )
        data = json.loads(result)
        if "error" in data:
            raise HTTPException(status_code=400, detail=data["error"])
        return {"ok": True, "activity": data}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
