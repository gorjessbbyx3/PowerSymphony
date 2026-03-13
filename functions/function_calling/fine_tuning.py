"""Model Fine-Tuning — OpenAI fine-tuning API tool functions.

Agents can use these tools to:
- Upload training datasets
- Create and monitor fine-tuning jobs
- List available fine-tuned models
- Cancel in-progress jobs

Requires: API_KEY or OPENAI_API_KEY environment variable pointing to OpenAI.
"""

import json
import os
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional


def _openai_request(method: str, path: str, body: Optional[Dict] = None,
                    files: Optional[bytes] = None, boundary: str = "") -> Dict[str, Any]:
    api_key = os.environ.get("API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"error": "API_KEY or OPENAI_API_KEY is not set."}
    url = f"https://api.openai.com/v1{path}"
    headers = {"Authorization": f"Bearer {api_key}"}
    data = None
    if files:
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        data = files
    elif body:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"OpenAI API {e.code}: {e.read().decode()[:500]}"}
    except Exception as exc:
        return {"error": str(exc)}


def finetune_upload_dataset(training_data: str, filename: str = "training_data.jsonl") -> str:
    """
    Upload a fine-tuning training dataset to OpenAI.
    The dataset must be in JSONL format, one example per line.
    Each line: {"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}

    Args:
        training_data (str): The full JSONL content with one example per line.
        filename (str): Filename to use for the uploaded file. Defaults to "training_data.jsonl".

    Returns:
        str: JSON with keys: file_id, filename, bytes, status.
    """
    api_key = os.environ.get("API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return json.dumps({"error": "API_KEY or OPENAI_API_KEY is not set."})

    # Validate a few lines
    lines = [l.strip() for l in training_data.strip().splitlines() if l.strip()]
    if not lines:
        return json.dumps({"error": "Training data is empty."})
    try:
        json.loads(lines[0])
    except json.JSONDecodeError:
        return json.dumps({"error": "Training data must be valid JSONL (one JSON object per line)."})

    # Build multipart/form-data
    boundary = "----PowerSymphonyBoundary7834560"
    file_bytes = training_data.encode("utf-8")
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="purpose"\r\n\r\n'
        f"fine-tune\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/json\r\n\r\n"
    ).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()

    result = _openai_request("POST", "/files", files=body, boundary=boundary)
    if "error" in result:
        return json.dumps(result)
    return json.dumps({
        "file_id": result.get("id"),
        "filename": result.get("filename"),
        "bytes": result.get("bytes"),
        "status": result.get("status"),
        "created_at": result.get("created_at"),
    }, indent=2)


def finetune_create_job(file_id: str, base_model: str = "gpt-4o-mini",
                        n_epochs: int = 3, suffix: str = "") -> str:
    """
    Start a fine-tuning job on OpenAI using a previously uploaded dataset.

    Args:
        file_id (str): The file ID returned from finetune_upload_dataset.
        base_model (str): The base model to fine-tune: gpt-4o-mini, gpt-3.5-turbo,
                          gpt-4o-mini-2024-07-18. Defaults to "gpt-4o-mini".
        n_epochs (int): Number of training epochs (1-10). Defaults to 3.
        suffix (str): Optional suffix to append to the fine-tuned model name, e.g. "my-assistant".

    Returns:
        str: JSON with keys: job_id, model, status, created_at, estimated_finish.
    """
    n_epochs = max(1, min(int(n_epochs), 10))
    body: Dict[str, Any] = {
        "training_file": file_id,
        "model": base_model,
        "hyperparameters": {"n_epochs": n_epochs},
    }
    if suffix:
        body["suffix"] = suffix[:18]  # OpenAI limit
    result = _openai_request("POST", "/fine_tuning/jobs", body)
    if "error" in result:
        return json.dumps(result)
    return json.dumps({
        "job_id": result.get("id"),
        "model": result.get("model"),
        "fine_tuned_model": result.get("fine_tuned_model"),
        "status": result.get("status"),
        "created_at": result.get("created_at"),
        "estimated_finish": result.get("estimated_finish"),
        "trained_tokens": result.get("trained_tokens"),
    }, indent=2)


def finetune_get_job_status(job_id: str) -> str:
    """
    Get the current status of a fine-tuning job.

    Args:
        job_id (str): The fine-tuning job ID, e.g. "ftjob-abc123".

    Returns:
        str: JSON with job_id, status, fine_tuned_model, trained_tokens, and events summary.
    """
    result = _openai_request("GET", f"/fine_tuning/jobs/{job_id}")
    if "error" in result:
        return json.dumps(result)

    events_result = _openai_request("GET", f"/fine_tuning/jobs/{job_id}/events?limit=5")
    recent_events = []
    if "data" in events_result:
        recent_events = [
            {"level": e.get("level"), "message": e.get("message"), "created_at": e.get("created_at")}
            for e in events_result["data"]
        ]

    return json.dumps({
        "job_id": result.get("id"),
        "status": result.get("status"),
        "model": result.get("model"),
        "fine_tuned_model": result.get("fine_tuned_model"),
        "trained_tokens": result.get("trained_tokens"),
        "training_file": result.get("training_file"),
        "created_at": result.get("created_at"),
        "finished_at": result.get("finished_at"),
        "recent_events": recent_events,
    }, indent=2)


def finetune_list_jobs(limit: int = 10) -> str:
    """
    List recent fine-tuning jobs.

    Args:
        limit (int): Number of jobs to return (1-20). Defaults to 10.

    Returns:
        str: JSON array of jobs with id, status, model, fine_tuned_model, and created_at.
    """
    limit = max(1, min(int(limit), 20))
    result = _openai_request("GET", f"/fine_tuning/jobs?limit={limit}")
    if "error" in result:
        return json.dumps(result)
    jobs = [
        {
            "job_id": j.get("id"),
            "status": j.get("status"),
            "model": j.get("model"),
            "fine_tuned_model": j.get("fine_tuned_model"),
            "created_at": j.get("created_at"),
            "trained_tokens": j.get("trained_tokens"),
        }
        for j in result.get("data", [])
    ]
    return json.dumps({"jobs": jobs, "count": len(jobs)}, indent=2)


def finetune_cancel_job(job_id: str) -> str:
    """
    Cancel a running fine-tuning job.

    Args:
        job_id (str): The fine-tuning job ID to cancel.

    Returns:
        str: JSON with job_id and new status.
    """
    result = _openai_request("POST", f"/fine_tuning/jobs/{job_id}/cancel")
    if "error" in result:
        return json.dumps(result)
    return json.dumps({
        "job_id": result.get("id"),
        "status": result.get("status"),
        "message": f"Job {job_id} has been cancelled.",
    }, indent=2)


def finetune_list_models() -> str:
    """
    List all available fine-tuned models in the OpenAI account.

    Returns:
        str: JSON array of fine-tuned models with id, created_at, and owned_by.
    """
    result = _openai_request("GET", "/models")
    if "error" in result:
        return json.dumps(result)
    ft_models = [
        {"id": m.get("id"), "created_at": m.get("created"), "owned_by": m.get("owned_by")}
        for m in result.get("data", [])
        if "ft:" in m.get("id", "") or "ftjob" in m.get("id", "") or m.get("owned_by", "").startswith("user-")
    ]
    return json.dumps({"fine_tuned_models": ft_models, "count": len(ft_models)}, indent=2)
