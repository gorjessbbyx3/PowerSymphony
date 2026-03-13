"""GitHub Copilot Synergy — tool functions for GitHub API integration.

Agents can use these tools to read/write repos, open PRs, create issues,
and search code — enabling real-time Copilot-style collaboration workflows.

Requires: GITHUB_TOKEN environment variable.
"""

import base64
import json
import os
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional


def _gh_request(method: str, path: str, body: Optional[Dict] = None) -> Dict[str, Any]:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return {"error": "GITHUB_TOKEN environment variable is not set."}
    url = f"https://api.github.com{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "PowerSymphony/1.0",
    }
    data = json.dumps(body).encode() if body else None
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"GitHub API {e.code}: {e.read().decode()[:500]}"}
    except Exception as exc:
        return {"error": str(exc)}


def github_list_repos(username: str) -> str:
    """
    List public repositories for a GitHub user or organization.

    Args:
        username (str): GitHub username or organization name.

    Returns:
        str: JSON array of repos with name, description, language, stars, url.
    """
    data = _gh_request("GET", f"/users/{username}/repos?sort=updated&per_page=20")
    if "error" in data:
        return json.dumps(data)
    result = [
        {
            "name": r.get("name"),
            "full_name": r.get("full_name"),
            "description": r.get("description"),
            "language": r.get("language"),
            "stars": r.get("stargazers_count"),
            "url": r.get("html_url"),
            "default_branch": r.get("default_branch"),
        }
        for r in (data if isinstance(data, list) else [])
    ]
    return json.dumps(result, indent=2)


def github_read_file(repo: str, path: str, branch: str = "main") -> str:
    """
    Read the contents of a file from a GitHub repository.

    Args:
        repo (str): Full repo name, e.g. "owner/repo".
        path (str): File path within the repo, e.g. "src/app.py".
        branch (str): Branch name. Defaults to "main".

    Returns:
        str: JSON with keys: path, content (decoded text), sha, size, encoding.
    """
    data = _gh_request("GET", f"/repos/{repo}/contents/{path}?ref={branch}")
    if "error" in data:
        return json.dumps(data)
    try:
        content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
    except Exception:
        content = "(binary file)"
    return json.dumps({
        "path": data.get("path"),
        "sha": data.get("sha"),
        "size": data.get("size"),
        "content": content,
    }, indent=2)


def github_list_files(repo: str, path: str = "", branch: str = "main") -> str:
    """
    List files and directories in a GitHub repository path.

    Args:
        repo (str): Full repo name, e.g. "owner/repo".
        path (str): Directory path within the repo. Empty string for root.
        branch (str): Branch name. Defaults to "main".

    Returns:
        str: JSON array of items with name, type (file/dir), path, size.
    """
    data = _gh_request("GET", f"/repos/{repo}/contents/{path}?ref={branch}")
    if "error" in data:
        return json.dumps(data)
    if not isinstance(data, list):
        data = [data]
    result = [
        {"name": item.get("name"), "type": item.get("type"), "path": item.get("path"), "size": item.get("size")}
        for item in data
    ]
    return json.dumps(result, indent=2)


def github_write_file(repo: str, path: str, content: str, message: str,
                      branch: str = "main", sha: str = "") -> str:
    """
    Create or update a file in a GitHub repository.

    Args:
        repo (str): Full repo name, e.g. "owner/repo".
        path (str): File path to create/update, e.g. "src/new_feature.py".
        content (str): Plain text content for the file.
        message (str): Commit message.
        branch (str): Branch to commit to. Defaults to "main".
        sha (str): The blob SHA of the file being replaced (required for updates, empty for new files).

    Returns:
        str: JSON with commit sha, file url, and status.
    """
    encoded = base64.b64encode(content.encode()).decode()
    body: Dict[str, Any] = {"message": message, "content": encoded, "branch": branch}
    if sha:
        body["sha"] = sha
    data = _gh_request("PUT", f"/repos/{repo}/contents/{path}", body)
    if "error" in data:
        return json.dumps(data)
    return json.dumps({
        "status": "ok",
        "commit_sha": data.get("commit", {}).get("sha"),
        "file_url": data.get("content", {}).get("html_url"),
        "path": path,
    }, indent=2)


def github_create_pull_request(repo: str, title: str, body: str,
                                head: str, base: str = "main") -> str:
    """
    Create a pull request in a GitHub repository.

    Args:
        repo (str): Full repo name, e.g. "owner/repo".
        title (str): PR title.
        body (str): PR description (supports Markdown).
        head (str): The branch name with the changes (source branch).
        base (str): The branch to merge into. Defaults to "main".

    Returns:
        str: JSON with PR number, url, and state.
    """
    data = _gh_request("POST", f"/repos/{repo}/pulls", {
        "title": title, "body": body, "head": head, "base": base
    })
    if "error" in data:
        return json.dumps(data)
    return json.dumps({
        "pr_number": data.get("number"),
        "url": data.get("html_url"),
        "state": data.get("state"),
        "title": data.get("title"),
    }, indent=2)


def github_create_issue(repo: str, title: str, body: str, labels: str = "") -> str:
    """
    Create a new issue in a GitHub repository.

    Args:
        repo (str): Full repo name, e.g. "owner/repo".
        title (str): Issue title.
        body (str): Issue description (supports Markdown).
        labels (str): Comma-separated list of label names, e.g. "bug,enhancement".

    Returns:
        str: JSON with issue number, url, and state.
    """
    payload: Dict[str, Any] = {"title": title, "body": body}
    if labels:
        payload["labels"] = [l.strip() for l in labels.split(",") if l.strip()]
    data = _gh_request("POST", f"/repos/{repo}/issues", payload)
    if "error" in data:
        return json.dumps(data)
    return json.dumps({
        "issue_number": data.get("number"),
        "url": data.get("html_url"),
        "state": data.get("state"),
        "title": data.get("title"),
    }, indent=2)


def github_search_code(query: str, repo: str = "") -> str:
    """
    Search for code across GitHub repositories.

    Args:
        query (str): Search keywords, e.g. "def authenticate" or "useState React".
        repo (str): Limit search to a specific repo, e.g. "owner/repo". Empty for global search.

    Returns:
        str: JSON array of results with file path, repo, url, and a text snippet.
    """
    q = query
    if repo:
        q += f" repo:{repo}"
    import urllib.parse
    encoded_q = urllib.parse.quote(q)
    data = _gh_request("GET", f"/search/code?q={encoded_q}&per_page=10")
    if "error" in data:
        return json.dumps(data)
    items = data.get("items", [])
    result = [
        {
            "path": item.get("path"),
            "repo": item.get("repository", {}).get("full_name"),
            "url": item.get("html_url"),
            "score": item.get("score"),
        }
        for item in items
    ]
    return json.dumps({"total": data.get("total_count", 0), "results": result}, indent=2)


def github_get_repo_info(repo: str) -> str:
    """
    Get detailed information about a GitHub repository.

    Args:
        repo (str): Full repo name, e.g. "owner/repo".

    Returns:
        str: JSON with name, description, language, stars, forks, open_issues, topics, clone_url.
    """
    data = _gh_request("GET", f"/repos/{repo}")
    if "error" in data:
        return json.dumps(data)
    return json.dumps({
        "name": data.get("name"),
        "full_name": data.get("full_name"),
        "description": data.get("description"),
        "language": data.get("language"),
        "stars": data.get("stargazers_count"),
        "forks": data.get("forks_count"),
        "open_issues": data.get("open_issues_count"),
        "topics": data.get("topics", []),
        "default_branch": data.get("default_branch"),
        "clone_url": data.get("clone_url"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
    }, indent=2)


def github_list_commits(repo: str, branch: str = "main", n: int = 10) -> str:
    """
    List recent commits on a branch of a GitHub repository.

    Args:
        repo (str): Full repo name, e.g. "owner/repo".
        branch (str): Branch name. Defaults to "main".
        n (int): Number of commits to return (1-30). Defaults to 10.

    Returns:
        str: JSON array with sha, message, author, and date.
    """
    n = max(1, min(int(n), 30))
    data = _gh_request("GET", f"/repos/{repo}/commits?sha={branch}&per_page={n}")
    if "error" in data:
        return json.dumps(data)
    if not isinstance(data, list):
        return json.dumps({"error": "Unexpected response", "raw": str(data)[:300]})
    result = [
        {
            "sha": c.get("sha", "")[:12],
            "message": c.get("commit", {}).get("message", "").split("\n")[0],
            "author": c.get("commit", {}).get("author", {}).get("name"),
            "date": c.get("commit", {}).get("author", {}).get("date"),
        }
        for c in data
    ]
    return json.dumps(result, indent=2)
