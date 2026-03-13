"""GitHub Copilot Synergy — REST API routes for GitHub integration."""

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/github", tags=["github"])


class RepoAnalysisRequest(BaseModel):
    repo: str
    question: str = "Summarize the architecture and main components of this repository."


class WriteFileRequest(BaseModel):
    repo: str
    path: str
    content: str
    message: str
    branch: str = "main"
    sha: str = ""


class CreatePRRequest(BaseModel):
    repo: str
    title: str
    body: str
    head: str
    base: str = "main"


class CreateIssueRequest(BaseModel):
    repo: str
    title: str
    body: str
    labels: str = ""


class SearchCodeRequest(BaseModel):
    query: str
    repo: str = ""


def _run_tool(func_name: str, **kwargs) -> Any:
    try:
        import importlib
        mod = importlib.import_module("functions.function_calling.github_tools")
        fn = getattr(mod, func_name)
        result = fn(**kwargs)
        return json.loads(result) if isinstance(result, str) else result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/repos/{username}")
async def list_repos(username: str) -> Dict[str, Any]:
    """List public repositories for a GitHub user or organization."""
    result = _run_tool("github_list_repos", username=username)
    return {"ok": True, "repos": result}


@router.get("/repo/{owner}/{repo_name}")
async def get_repo(owner: str, repo_name: str) -> Dict[str, Any]:
    """Get detailed information about a repository."""
    result = _run_tool("github_get_repo_info", repo=f"{owner}/{repo_name}")
    return {"ok": True, "repo": result}


@router.get("/files/{owner}/{repo_name}")
async def list_files(owner: str, repo_name: str, path: str = "", branch: str = "main") -> Dict[str, Any]:
    """List files in a repository directory."""
    result = _run_tool("github_list_files", repo=f"{owner}/{repo_name}", path=path, branch=branch)
    return {"ok": True, "files": result}


@router.get("/file/{owner}/{repo_name}")
async def read_file(owner: str, repo_name: str, path: str, branch: str = "main") -> Dict[str, Any]:
    """Read the contents of a file from a repository."""
    result = _run_tool("github_read_file", repo=f"{owner}/{repo_name}", path=path, branch=branch)
    return {"ok": True, "file": result}


@router.get("/commits/{owner}/{repo_name}")
async def list_commits(owner: str, repo_name: str, branch: str = "main", n: int = 10) -> Dict[str, Any]:
    """List recent commits on a branch."""
    result = _run_tool("github_list_commits", repo=f"{owner}/{repo_name}", branch=branch, n=n)
    return {"ok": True, "commits": result}


@router.post("/write-file")
async def write_file(req: WriteFileRequest) -> Dict[str, Any]:
    """Create or update a file in a repository."""
    result = _run_tool("github_write_file",
                        repo=req.repo, path=req.path, content=req.content,
                        message=req.message, branch=req.branch, sha=req.sha)
    return {"ok": True, "result": result}


@router.post("/pull-request")
async def create_pr(req: CreatePRRequest) -> Dict[str, Any]:
    """Create a pull request."""
    result = _run_tool("github_create_pull_request",
                        repo=req.repo, title=req.title, body=req.body,
                        head=req.head, base=req.base)
    return {"ok": True, "pr": result}


@router.post("/issue")
async def create_issue(req: CreateIssueRequest) -> Dict[str, Any]:
    """Create a new issue."""
    result = _run_tool("github_create_issue",
                        repo=req.repo, title=req.title, body=req.body, labels=req.labels)
    return {"ok": True, "issue": result}


@router.post("/search")
async def search_code(req: SearchCodeRequest) -> Dict[str, Any]:
    """Search for code across GitHub."""
    result = _run_tool("github_search_code", query=req.query, repo=req.repo)
    return {"ok": True, "results": result}


@router.post("/analyze")
async def analyze_repo(req: RepoAnalysisRequest) -> Dict[str, Any]:
    """Use an AI agent to analyze a GitHub repository and answer questions about it."""
    import os
    api_key = os.environ.get("API_KEY") or os.environ.get("OPENAI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    # Gather repo context
    repo_info = _run_tool("github_get_repo_info", repo=req.repo)
    files = _run_tool("github_list_files", repo=req.repo, path="", branch="main")
    commits = _run_tool("github_list_commits", repo=req.repo, n=5)

    context = json.dumps({
        "repo_info": repo_info,
        "root_files": files[:20] if isinstance(files, list) else files,
        "recent_commits": commits,
    }, indent=2)

    answer = "AI analysis requires API_KEY or ANTHROPIC_API_KEY to be configured."

    if anthropic_key and not api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            msg = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                messages=[{"role": "user", "content": f"Repo context:\n{context}\n\nQuestion: {req.question}"}],
            )
            answer = msg.content[0].text
        except Exception as exc:
            answer = str(exc)
    elif api_key:
        try:
            import openai
            client = openai.OpenAI(api_key=api_key, base_url=os.environ.get("BASE_URL", "https://api.openai.com/v1"))
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful code analyst. Answer questions about GitHub repositories concisely."},
                    {"role": "user", "content": f"Repo context:\n{context}\n\nQuestion: {req.question}"},
                ],
                max_tokens=1024,
            )
            answer = resp.choices[0].message.content
        except Exception as exc:
            answer = str(exc)

    return {"ok": True, "repo": req.repo, "question": req.question, "answer": answer, "context": {"repo_info": repo_info}}
