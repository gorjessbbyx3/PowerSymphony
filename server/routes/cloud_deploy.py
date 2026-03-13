"""REST API for cloud deployments (AWS S3, Google Cloud Storage, GitHub Releases)."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

router = APIRouter(prefix="/api/deploy", tags=["cloud_deploy"])

_DEPLOY_LOG_PATH = Path("WareHouse/.deployments.jsonl")


class S3DeployRequest(BaseModel):
    local_path: str
    bucket: str
    key: str = ""
    public: bool = False
    content_type: str = ""


class GCSDeployRequest(BaseModel):
    local_path: str
    bucket: str
    blob_name: str = ""
    public: bool = False


class GitHubReleaseRequest(BaseModel):
    repo: str
    tag: str
    title: str
    body: str = ""
    file_path: str = ""
    draft: bool = False


class StaticSiteRequest(BaseModel):
    content: str
    title: str = "Generated Site"
    output_dir: str = "WareHouse/static_site"


@router.get("/status")
async def deploy_status() -> Dict[str, Any]:
    """Check which cloud deployment providers are configured via env vars."""
    return {
        "providers": {
            "s3": {
                "configured": bool(os.environ.get("AWS_ACCESS_KEY_ID")),
                "hint": "Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION.",
            },
            "gcs": {
                "configured": bool(
                    os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or
                    os.environ.get("GOOGLE_CLOUD_PROJECT")
                ),
                "hint": "Set GOOGLE_APPLICATION_CREDENTIALS to your service-account JSON path.",
            },
            "github": {
                "configured": bool(
                    os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
                ),
                "hint": "Set GITHUB_TOKEN with repo and write:packages scopes.",
            },
        }
    }


@router.post("/s3")
async def deploy_s3(req: S3DeployRequest) -> Dict[str, Any]:
    """Upload a local file from the server to AWS S3."""
    try:
        from functions.function_calling.cloud_deploy import deploy_to_s3
        result = deploy_to_s3(
            req.local_path, bucket=req.bucket, key=req.key,
            public=req.public, content_type=req.content_type,
        )
        data = json.loads(result)
        if "error" in data:
            raise HTTPException(status_code=400, detail=data["error"])
        return data
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/gcs")
async def deploy_gcs(req: GCSDeployRequest) -> Dict[str, Any]:
    """Upload a local file from the server to Google Cloud Storage."""
    try:
        from functions.function_calling.cloud_deploy import deploy_to_gcs
        result = deploy_to_gcs(
            req.local_path, bucket=req.bucket,
            blob_name=req.blob_name, public=req.public,
        )
        data = json.loads(result)
        if "error" in data:
            raise HTTPException(status_code=400, detail=data["error"])
        return data
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/github-release")
async def deploy_github_release(req: GitHubReleaseRequest) -> Dict[str, Any]:
    """Create a GitHub Release, optionally attaching a file as an asset."""
    try:
        from functions.function_calling.cloud_deploy import deploy_to_github_release
        result = deploy_to_github_release(
            req.repo, tag=req.tag, title=req.title, body=req.body,
            file_path=req.file_path, draft=req.draft,
        )
        data = json.loads(result)
        if "error" in data:
            raise HTTPException(status_code=400, detail=data["error"])
        return data
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/generate-site")
async def generate_static_site(req: StaticSiteRequest) -> Dict[str, Any]:
    """
    Generate a minimal static HTML site from Markdown content.
    Returned files can then be deployed to S3/GCS.
    """
    try:
        from functions.function_calling.cloud_deploy import generate_static_site
        result = generate_static_site(req.content, title=req.title, output_dir=req.output_dir)
        data = json.loads(result)
        if "error" in data:
            raise HTTPException(status_code=400, detail=data["error"])
        return data
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/history")
async def deployment_history(limit: int = 20) -> Dict[str, Any]:
    """Return a list of past deployments made by workflow agents or the API."""
    try:
        from functions.function_calling.cloud_deploy import list_deployment_history
        result = list_deployment_history(limit=limit)
        return {"ok": True, "deployments": json.loads(result)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
