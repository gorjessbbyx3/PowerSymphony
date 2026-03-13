"""CI/CD Automation — REST API routes for pipeline generation."""

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/cicd", tags=["cicd"])


class GitHubActionsRequest(BaseModel):
    project_name: str
    language: str
    test_command: str = ""
    deploy_target: str = "none"
    branch: str = "main"


class DockerfileRequest(BaseModel):
    language: str
    app_port: int = 8000
    entry_point: str = ""


class DockerComposeRequest(BaseModel):
    services: str
    with_database: str = "none"


class AWSCodePipelineRequest(BaseModel):
    project_name: str
    repo_owner: str
    repo_name: str
    deploy_stack: str = "ecs"


def _run_tool(func_name: str, **kwargs) -> Any:
    try:
        import importlib
        mod = importlib.import_module("functions.function_calling.cicd")
        fn = getattr(mod, func_name)
        result = fn(**kwargs)
        return json.loads(result) if isinstance(result, str) else result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/github-actions")
async def generate_github_actions(req: GitHubActionsRequest) -> Dict[str, Any]:
    """Generate a GitHub Actions CI/CD workflow YAML."""
    result = _run_tool("generate_github_actions",
                        project_name=req.project_name, language=req.language,
                        test_command=req.test_command, deploy_target=req.deploy_target,
                        branch=req.branch)
    return {"ok": True, **result}


@router.post("/dockerfile")
async def generate_dockerfile(req: DockerfileRequest) -> Dict[str, Any]:
    """Generate an optimized Dockerfile."""
    result = _run_tool("generate_dockerfile",
                        language=req.language, app_port=req.app_port, entry_point=req.entry_point)
    return {"ok": True, **result}


@router.post("/docker-compose")
async def generate_docker_compose(req: DockerComposeRequest) -> Dict[str, Any]:
    """Generate a docker-compose.yml for multi-service apps."""
    result = _run_tool("generate_docker_compose",
                        services=req.services, with_database=req.with_database)
    return {"ok": True, **result}


@router.post("/aws-codepipeline")
async def generate_aws_pipeline(req: AWSCodePipelineRequest) -> Dict[str, Any]:
    """Generate an AWS CodePipeline CloudFormation template."""
    result = _run_tool("generate_aws_codepipeline",
                        project_name=req.project_name, repo_owner=req.repo_owner,
                        repo_name=req.repo_name, deploy_stack=req.deploy_stack)
    return {"ok": True, **result}


@router.get("/templates")
async def list_templates() -> Dict[str, Any]:
    """List all available CI/CD pipeline templates."""
    return {
        "ok": True,
        "templates": [
            {
                "id": "github-actions",
                "name": "GitHub Actions",
                "description": "Complete CI/CD workflow with build, test, and deploy stages",
                "languages": ["python", "node", "go", "rust", "java"],
                "deploy_targets": ["none", "vercel", "netlify", "docker-hub", "aws-eb", "heroku"],
            },
            {
                "id": "dockerfile",
                "name": "Dockerfile",
                "description": "Optimized multi-stage Dockerfile for containerization",
                "languages": ["python", "node", "go", "rust", "java"],
                "deploy_targets": [],
            },
            {
                "id": "docker-compose",
                "name": "Docker Compose",
                "description": "Multi-service docker-compose.yml with optional database",
                "languages": [],
                "deploy_targets": ["postgres", "mysql", "mongodb", "redis"],
            },
            {
                "id": "aws-codepipeline",
                "name": "AWS CodePipeline",
                "description": "CloudFormation template for AWS CodePipeline + CodeBuild",
                "languages": [],
                "deploy_targets": ["ecs", "lambda", "s3", "eb"],
            },
        ],
    }
