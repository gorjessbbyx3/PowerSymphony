"""Marketplace — REST API for discovering, publishing, and downloading workflow templates."""

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])

MARKET_DIR = Path("WareHouse/.marketplace")
LISTINGS_FILE = MARKET_DIR / "listings.jsonl"
MARKET_DIR.mkdir(parents=True, exist_ok=True)


def _load_listings() -> List[Dict]:
    if not LISTINGS_FILE.exists():
        return []
    listings = []
    for line in LISTINGS_FILE.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                listings.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return listings


def _save_listings(listings: List[Dict]) -> None:
    LISTINGS_FILE.write_text("\n".join(json.dumps(l) for l in listings) + "\n")


def _seed_default_listings():
    """Seed the marketplace with built-in workflow templates on first run."""
    if LISTINGS_FILE.exists() and LISTINGS_FILE.stat().st_size > 0:
        return
    defaults = [
        {
            "id": "ps-chatdev-v1",
            "name": "ChatDev Full Cycle",
            "description": "Complete multi-agent software development workflow: planning, coding, review, and testing loops. Based on the ChatDev paper.",
            "category": "development",
            "tags": ["multi-agent", "code-gen", "testing", "review"],
            "author": "PowerSymphony",
            "yaml_file": "ChatDev_v1.yaml",
            "downloads": 142,
            "rating": 4.7,
            "ratings_count": 31,
            "created_at": 1710000000,
            "featured": True,
        },
        {
            "id": "ps-dev-swarm",
            "name": "DevSwarm: Plan→Code→Test→Deploy",
            "description": "Six-agent swarm that takes a feature request from planning through deployment. Includes Tech Lead, Backend Dev, Frontend Dev, QA, and DevOps agents.",
            "category": "development",
            "tags": ["swarm", "ci-cd", "full-stack", "planning"],
            "author": "PowerSymphony",
            "yaml_file": "dev_swarm.yaml",
            "downloads": 89,
            "rating": 4.8,
            "ratings_count": 18,
            "created_at": 1711000000,
            "featured": True,
        },
        {
            "id": "ps-code-review-swarm",
            "name": "Code Review Swarm",
            "description": "Three specialized reviewers (security, performance, maintainability) plus an aggregator that synthesizes a comprehensive review report.",
            "category": "code-quality",
            "tags": ["review", "security", "performance", "swarm"],
            "author": "PowerSymphony",
            "yaml_file": "code_review_swarm.yaml",
            "downloads": 67,
            "rating": 4.6,
            "ratings_count": 14,
            "created_at": 1711100000,
            "featured": False,
        },
        {
            "id": "ps-blockchain-builder",
            "name": "Blockchain dApp Builder",
            "description": "Generate Solidity smart contracts, deploy scripts, and a React dApp frontend. Supports ERC-20/721 tokens, DeFi patterns, and multi-signature wallets.",
            "category": "blockchain",
            "tags": ["solidity", "web3", "smart-contracts", "defi"],
            "author": "PowerSymphony",
            "yaml_file": "blockchain_builder.yaml",
            "downloads": 55,
            "rating": 4.5,
            "ratings_count": 11,
            "created_at": 1711200000,
            "featured": True,
        },
        {
            "id": "ps-tourism-app",
            "name": "Tourism App Builder",
            "description": "Build geo-aware tourism applications with real location APIs, itinerary generation, attraction discovery, and weather integration.",
            "category": "travel",
            "tags": ["geo", "maps", "tourism", "itinerary", "hawaii"],
            "author": "PowerSymphony",
            "yaml_file": "tourism_app.yaml",
            "downloads": 43,
            "rating": 4.4,
            "ratings_count": 9,
            "created_at": 1711300000,
            "featured": False,
        },
        {
            "id": "ps-fintech-api",
            "name": "Fintech API Generator",
            "description": "Generate production-ready financial APIs with live market data, transaction processing, portfolio analytics, and compliance checks.",
            "category": "finance",
            "tags": ["fintech", "api", "stocks", "crypto", "payments"],
            "author": "PowerSymphony",
            "yaml_file": "fintech_api.yaml",
            "downloads": 38,
            "rating": 4.3,
            "ratings_count": 8,
            "created_at": 1711400000,
            "featured": False,
        },
        {
            "id": "ps-cicd-generator",
            "name": "CI/CD Pipeline Generator",
            "description": "Describe your project and get complete GitHub Actions, Dockerfile, and docker-compose configurations ready to use.",
            "category": "devops",
            "tags": ["ci-cd", "github-actions", "docker", "aws"],
            "author": "PowerSymphony",
            "yaml_file": "cicd_generator.yaml",
            "downloads": 91,
            "rating": 4.9,
            "ratings_count": 22,
            "created_at": 1711500000,
            "featured": True,
        },
        {
            "id": "ps-qa-swarm",
            "name": "QA Test Swarm",
            "description": "Multi-agent QA pipeline that writes unit tests, integration tests, and edge case scenarios, then generates a complete test coverage report.",
            "category": "testing",
            "tags": ["testing", "qa", "unit-tests", "coverage"],
            "author": "PowerSymphony",
            "yaml_file": "qa_swarm.yaml",
            "downloads": 72,
            "rating": 4.6,
            "ratings_count": 16,
            "created_at": 1711600000,
            "featured": False,
        },
    ]
    _save_listings(defaults)


_seed_default_listings()


class PublishRequest(BaseModel):
    name: str
    description: str
    category: str
    tags: str = ""
    author: str = "anonymous"
    yaml_content: str


class RatingRequest(BaseModel):
    rating: float


@router.get("")
async def list_listings(
    category: str = "", search: str = "", featured: bool = False, limit: int = 50
) -> Dict[str, Any]:
    """Browse available marketplace listings."""
    listings = _load_listings()
    if category:
        listings = [l for l in listings if l.get("category") == category]
    if featured:
        listings = [l for l in listings if l.get("featured")]
    if search:
        q = search.lower()
        listings = [l for l in listings if
                     q in l.get("name", "").lower() or
                     q in l.get("description", "").lower() or
                     any(q in t for t in l.get("tags", []))]
    listings = sorted(listings, key=lambda l: l.get("downloads", 0), reverse=True)[:limit]
    return {"ok": True, "listings": listings, "count": len(listings)}


@router.get("/categories")
async def list_categories() -> Dict[str, Any]:
    """List all available categories with item counts."""
    listings = _load_listings()
    cats: Dict[str, int] = {}
    for l in listings:
        c = l.get("category", "other")
        cats[c] = cats.get(c, 0) + 1
    return {"ok": True, "categories": [{"name": k, "count": v} for k, v in sorted(cats.items())]}


@router.get("/featured")
async def featured_listings() -> Dict[str, Any]:
    """Get featured marketplace listings."""
    listings = [l for l in _load_listings() if l.get("featured")]
    return {"ok": True, "listings": listings}


@router.get("/{listing_id}")
async def get_listing(listing_id: str) -> Dict[str, Any]:
    """Get details for a specific listing."""
    for l in _load_listings():
        if l["id"] == listing_id:
            return {"ok": True, "listing": l}
    raise HTTPException(status_code=404, detail=f"Listing '{listing_id}' not found.")


@router.get("/{listing_id}/download")
async def download_listing(listing_id: str) -> Dict[str, Any]:
    """Download a workflow template. Returns the YAML content."""
    listings = _load_listings()
    for i, l in enumerate(listings):
        if l["id"] == listing_id:
            yaml_file = l.get("yaml_file", "")
            yaml_content = l.get("yaml_content", "")
            if yaml_file and not yaml_content:
                yaml_path = Path("yaml_instance") / yaml_file
                if yaml_path.exists():
                    yaml_content = yaml_path.read_text()
            if not yaml_content:
                raise HTTPException(status_code=404, detail="YAML content not available for this listing.")
            listings[i]["downloads"] = listings[i].get("downloads", 0) + 1
            _save_listings(listings)
            return {"ok": True, "listing_id": listing_id, "name": l["name"],
                    "yaml_content": yaml_content, "yaml_file": yaml_file}
    raise HTTPException(status_code=404, detail=f"Listing '{listing_id}' not found.")


@router.post("/publish")
async def publish_listing(req: PublishRequest) -> Dict[str, Any]:
    """Publish a workflow template to the marketplace."""
    if len(req.yaml_content.strip()) < 20:
        raise HTTPException(status_code=400, detail="YAML content is too short to be a valid workflow.")
    listing_id = f"user-{uuid.uuid4().hex[:10]}"
    tags = [t.strip() for t in req.tags.split(",") if t.strip()]
    listing = {
        "id": listing_id,
        "name": req.name,
        "description": req.description,
        "category": req.category,
        "tags": tags,
        "author": req.author,
        "yaml_content": req.yaml_content,
        "yaml_file": "",
        "downloads": 0,
        "rating": 0.0,
        "ratings_count": 0,
        "created_at": int(time.time()),
        "featured": False,
    }
    listings = _load_listings()
    listings.append(listing)
    _save_listings(listings)
    return {"ok": True, "listing_id": listing_id, "message": "Workflow published successfully."}


@router.post("/{listing_id}/rate")
async def rate_listing(listing_id: str, req: RatingRequest) -> Dict[str, Any]:
    """Rate a marketplace listing (1.0 - 5.0)."""
    if not (1.0 <= req.rating <= 5.0):
        raise HTTPException(status_code=400, detail="Rating must be between 1.0 and 5.0.")
    listings = _load_listings()
    for i, l in enumerate(listings):
        if l["id"] == listing_id:
            old_total = l.get("rating", 0.0) * l.get("ratings_count", 0)
            new_count = l.get("ratings_count", 0) + 1
            new_rating = (old_total + req.rating) / new_count
            listings[i]["rating"] = round(new_rating, 2)
            listings[i]["ratings_count"] = new_count
            _save_listings(listings)
            return {"ok": True, "listing_id": listing_id, "new_rating": round(new_rating, 2), "ratings_count": new_count}
    raise HTTPException(status_code=404, detail=f"Listing '{listing_id}' not found.")
