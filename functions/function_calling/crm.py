"""CRM integration tool functions for workflow agents (HubSpot)."""

import json
import os
from typing import Any, Dict, List, Optional


def _hubspot_request(method: str, path: str, payload: Optional[Dict] = None) -> Dict:
    """Internal helper for HubSpot API calls."""
    import requests

    token = os.environ.get("HUBSPOT_API_KEY") or os.environ.get("HUBSPOT_ACCESS_TOKEN")
    if not token:
        return {"error": "HUBSPOT_API_KEY or HUBSPOT_ACCESS_TOKEN environment variable is not set."}

    base = "https://api.hubapi.com"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    url = f"{base}{path}"
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=15)
        elif method == "POST":
            resp = requests.post(url, headers=headers, json=payload or {}, timeout=15)
        elif method == "PATCH":
            resp = requests.patch(url, headers=headers, json=payload or {}, timeout=15)
        elif method == "DELETE":
            resp = requests.delete(url, headers=headers, timeout=15)
        else:
            return {"error": f"Unsupported method: {method}"}
        if resp.status_code in (200, 201, 204):
            return resp.json() if resp.content else {"ok": True}
        return {"error": f"HTTP {resp.status_code}", "details": resp.text[:500]}
    except Exception as exc:
        return {"error": str(exc)}


def crm_search_contacts(query: str, limit: int = 10) -> str:
    """
    Search HubSpot CRM contacts by name or email.

    Args:
        query (str): The search query (name, email, or keyword).
        limit (int): Maximum number of contacts to return. Defaults to 10.

    Returns:
        str: JSON array of matching contacts with id, email, firstname, lastname.
    """
    payload = {
        "query": query,
        "limit": min(limit, 100),
        "properties": ["email", "firstname", "lastname", "phone", "company"],
    }
    result = _hubspot_request("POST", "/crm/v3/objects/contacts/search", payload)
    if "error" in result:
        return json.dumps(result)
    contacts = [
        {
            "id": c.get("id"),
            "email": c.get("properties", {}).get("email"),
            "firstname": c.get("properties", {}).get("firstname"),
            "lastname": c.get("properties", {}).get("lastname"),
            "phone": c.get("properties", {}).get("phone"),
            "company": c.get("properties", {}).get("company"),
        }
        for c in result.get("results", [])
    ]
    return json.dumps(contacts, ensure_ascii=False, indent=2)


def crm_create_contact(email: str, firstname: str = "", lastname: str = "", extra_properties: str = "{}") -> str:
    """
    Create a new contact in HubSpot CRM.

    Args:
        email (str): The contact's email address (required).
        firstname (str): The contact's first name.
        lastname (str): The contact's last name.
        extra_properties (str): JSON object of additional HubSpot properties,
                                e.g. '{"phone": "+1234567890", "company": "Acme"}' .

    Returns:
        str: JSON object with the created contact's id and properties, or an error.
    """
    try:
        extra = json.loads(extra_properties)
    except json.JSONDecodeError:
        extra = {}

    props: Dict[str, str] = {"email": email}
    if firstname:
        props["firstname"] = firstname
    if lastname:
        props["lastname"] = lastname
    props.update({k: str(v) for k, v in extra.items()})

    result = _hubspot_request("POST", "/crm/v3/objects/contacts", {"properties": props})
    return json.dumps(result, ensure_ascii=False, indent=2)


def crm_update_contact(contact_id: str, properties: str) -> str:
    """
    Update an existing HubSpot CRM contact.

    Args:
        contact_id (str): The HubSpot contact ID to update.
        properties (str): JSON object of properties to update,
                          e.g. '{"phone": "+1555000000", "lifecyclestage": "customer"}' .

    Returns:
        str: JSON object with updated contact data, or an error.
    """
    try:
        props: Dict[str, Any] = json.loads(properties)
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"Invalid properties JSON: {exc}"})

    result = _hubspot_request("PATCH", f"/crm/v3/objects/contacts/{contact_id}", {"properties": props})
    return json.dumps(result, ensure_ascii=False, indent=2)


def crm_list_deals(limit: int = 10, pipeline: str = "") -> str:
    """
    List deals from HubSpot CRM, optionally filtered by pipeline.

    Args:
        limit (int): Maximum number of deals to return. Defaults to 10.
        pipeline (str): Filter by pipeline ID (leave empty for all pipelines).

    Returns:
        str: JSON array of deals with id, name, amount, stage, pipeline.
    """
    params = f"?limit={min(limit, 100)}&properties=dealname,amount,dealstage,pipeline,closedate"
    result = _hubspot_request("GET", f"/crm/v3/objects/deals{params}")
    if "error" in result:
        return json.dumps(result)

    deals = []
    for d in result.get("results", []):
        props = d.get("properties", {})
        if pipeline and props.get("pipeline") != pipeline:
            continue
        deals.append({
            "id": d.get("id"),
            "name": props.get("dealname"),
            "amount": props.get("amount"),
            "stage": props.get("dealstage"),
            "pipeline": props.get("pipeline"),
            "close_date": props.get("closedate"),
        })
    return json.dumps(deals, ensure_ascii=False, indent=2)


def crm_create_deal(dealname: str, amount: float = 0, stage: str = "appointmentscheduled",
                    pipeline: str = "default", contact_id: str = "") -> str:
    """
    Create a new deal in HubSpot CRM and optionally associate it with a contact.

    Args:
        dealname (str): The name/title of the deal.
        amount (float): The deal value in the account currency. Defaults to 0.
        stage (str): The deal stage ID (e.g. 'appointmentscheduled', 'qualifiedtobuy',
                     'presentationscheduled', 'decisionmakerboughtin', 'contractsent',
                     'closedwon', 'closedlost'). Defaults to 'appointmentscheduled'.
        pipeline (str): The pipeline ID. Defaults to 'default'.
        contact_id (str): Optional HubSpot contact ID to associate with this deal.

    Returns:
        str: JSON object with the created deal's id and properties, or an error.
    """
    props = {
        "dealname": dealname,
        "amount": str(amount),
        "dealstage": stage,
        "pipeline": pipeline,
    }
    result = _hubspot_request("POST", "/crm/v3/objects/deals", {"properties": props})
    if "error" in result:
        return json.dumps(result)

    deal_id = result.get("id")
    if deal_id and contact_id:
        # Associate deal with contact
        assoc_payload = {
            "inputs": [{"from": {"id": deal_id}, "to": {"id": contact_id}, "type": "deal_to_contact"}]
        }
        _hubspot_request("POST", "/crm/v3/associations/deals/contacts/batch/create", assoc_payload)

    return json.dumps(result, ensure_ascii=False, indent=2)


def crm_log_activity(contact_id: str, subject: str, body: str, activity_type: str = "NOTE") -> str:
    """
    Log an activity (note, call, email) against a HubSpot contact.

    Args:
        contact_id (str): The HubSpot contact ID.
        subject (str): Subject / title of the activity.
        body (str): Body text / description of the activity.
        activity_type (str): Type of engagement: 'NOTE', 'CALL', or 'EMAIL'. Defaults to 'NOTE'.

    Returns:
        str: JSON object with the created engagement id, or an error.
    """
    valid_types = {"NOTE", "CALL", "EMAIL"}
    activity_type = activity_type.upper()
    if activity_type not in valid_types:
        return json.dumps({"error": f"activity_type must be one of {valid_types}"})

    payload = {
        "engagement": {"active": True, "type": activity_type},
        "associations": {"contactIds": [int(contact_id)]},
        "metadata": {"body": body, "subject": subject},
    }
    result = _hubspot_request("POST", "/engagements/v1/engagements", payload)
    return json.dumps(result, ensure_ascii=False, indent=2)
