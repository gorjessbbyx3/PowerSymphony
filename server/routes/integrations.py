"""API routes for managing third-party integrations (API keys, connections)."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from server.services.db import get_cursor

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


class IntegrationConfig(BaseModel):
    provider: str  # e.g. "adobe_firefly", "openai_dalle", "stability_ai"
    api_key: str
    enabled: bool = True
    label: Optional[str] = None
    base_url: Optional[str] = None


# ---------------------------------------------------------------------------
# DB helpers — integrations table
# ---------------------------------------------------------------------------

def _ensure_table():
    with get_cursor(dict_cursor=False) as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS integrations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                provider VARCHAR(100) NOT NULL,
                api_key TEXT NOT NULL,
                enabled BOOLEAN DEFAULT TRUE,
                label VARCHAR(255),
                base_url TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(user_id, provider)
            );
            CREATE INDEX IF NOT EXISTS idx_integrations_user_id ON integrations(user_id);
        """)


_ensure_table()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("")
async def list_integrations(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    with get_cursor() as cur:
        cur.execute(
            "SELECT id, provider, enabled, label, base_url, created_at FROM integrations WHERE user_id = %s ORDER BY provider",
            (user["id"],),
        )
        rows = cur.fetchall()

    # Mask API keys — only show last 4 chars
    integrations = []
    for row in rows:
        integrations.append({
            **dict(row),
            "api_key_hint": "••••" + row.get("api_key", "")[-4:] if row.get("api_key") else None,
            "created_at": str(row["created_at"]) if row.get("created_at") else None,
        })

    return {"integrations": integrations}


@router.post("")
async def save_integration(req: IntegrationConfig, request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO integrations (user_id, provider, api_key, enabled, label, base_url)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, provider) DO UPDATE SET
                api_key = EXCLUDED.api_key,
                enabled = EXCLUDED.enabled,
                label = EXCLUDED.label,
                base_url = EXCLUDED.base_url,
                updated_at = NOW()
            RETURNING id, provider, enabled, label
            """,
            (user["id"], req.provider, req.api_key, req.enabled, req.label, req.base_url),
        )
        row = cur.fetchone()

    return {"ok": True, "integration": dict(row)}


@router.delete("/{provider}")
async def delete_integration(provider: str, request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    with get_cursor() as cur:
        cur.execute(
            "DELETE FROM integrations WHERE user_id = %s AND provider = %s",
            (user["id"], provider),
        )

    return {"ok": True}


@router.get("/key/{provider}")
async def get_integration_key(provider: str, request: Request):
    """Internal endpoint — returns the raw API key for a provider (used by backend services)."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    with get_cursor() as cur:
        cur.execute(
            "SELECT api_key FROM integrations WHERE user_id = %s AND provider = %s AND enabled = TRUE",
            (user["id"], provider),
        )
        row = cur.fetchone()

    if not row:
        return {"api_key": None}
    return {"api_key": row["api_key"]}
