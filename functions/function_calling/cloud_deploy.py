"""Cloud deployment tool functions for workflow agents (AWS S3, GCS, GitHub)."""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

_DEPLOY_LOG_PATH = Path("WareHouse/.deployments.jsonl")


def _log_deployment(record: Dict[str, Any]) -> None:
    """Append a deployment record to the local history log."""
    try:
        _DEPLOY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _DEPLOY_LOG_PATH.open("a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass


def deploy_to_s3(local_path: str, bucket: str, key: str = "",
                 public: bool = False, content_type: str = "") -> str:
    """
    Upload a local file to an AWS S3 bucket.

    Args:
        local_path (str): Path to the local file to upload.
        bucket (str): Target S3 bucket name.
        key (str): S3 object key (path inside bucket). Defaults to the filename.
        public (bool): If True, set the object to public-read ACL. Defaults to False.
        content_type (str): MIME type override. Auto-detected if empty.

    Returns:
        str: JSON with the S3 URL and metadata on success, or an error message.
    """
    import boto3
    import mimetypes
    from botocore.exceptions import BotoCoreError, ClientError

    path = Path(local_path)
    if not path.exists():
        return json.dumps({"error": f"File not found: {local_path}"})

    object_key = key or path.name
    detected_type, _ = mimetypes.guess_type(str(path))
    mime = content_type or detected_type or "application/octet-stream"

    try:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region_name=os.environ.get("AWS_REGION", "us-east-1"),
        )
        extra_args: Dict[str, Any] = {"ContentType": mime}
        if public:
            extra_args["ACL"] = "public-read"

        s3.upload_file(str(path), bucket, object_key, ExtraArgs=extra_args)
        region = os.environ.get("AWS_REGION", "us-east-1")
        url = f"https://{bucket}.s3.{region}.amazonaws.com/{object_key}"
        record = {
            "provider": "s3", "bucket": bucket, "key": object_key,
            "url": url, "timestamp": time.time(),
        }
        _log_deployment(record)
        return json.dumps({"ok": True, "url": url, "bucket": bucket, "key": object_key})
    except (BotoCoreError, ClientError) as exc:
        return json.dumps({"error": str(exc)})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def deploy_to_gcs(local_path: str, bucket: str, blob_name: str = "", public: bool = False) -> str:
    """
    Upload a local file to a Google Cloud Storage bucket.

    Args:
        local_path (str): Path to the local file to upload.
        bucket (str): Target GCS bucket name.
        blob_name (str): Object name inside the bucket. Defaults to the filename.
        public (bool): If True, make the object publicly accessible. Defaults to False.

    Returns:
        str: JSON with the GCS URL and metadata on success, or an error message.
    """
    from google.cloud import storage as gcs_storage

    path = Path(local_path)
    if not path.exists():
        return json.dumps({"error": f"File not found: {local_path}"})

    name = blob_name or path.name

    try:
        client = gcs_storage.Client()
        bucket_obj = client.bucket(bucket)
        blob = bucket_obj.blob(name)
        blob.upload_from_filename(str(path))
        if public:
            blob.make_public()
            url = blob.public_url
        else:
            url = f"gs://{bucket}/{name}"
        record = {
            "provider": "gcs", "bucket": bucket, "blob": name,
            "url": url, "timestamp": time.time(),
        }
        _log_deployment(record)
        return json.dumps({"ok": True, "url": url, "bucket": bucket, "blob": name})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def deploy_to_github_release(repo: str, tag: str, title: str, body: str = "",
                             file_path: str = "", draft: bool = False) -> str:
    """
    Create a GitHub Release (and optionally attach a file as an asset).

    Args:
        repo (str): GitHub repository in 'owner/repo' format, e.g. 'acme/my-app'.
        tag (str): Git tag name for the release, e.g. 'v1.2.0'.
        title (str): Release title / name.
        body (str): Release notes / description (Markdown supported).
        file_path (str): Optional path to a local file to upload as a release asset.
        draft (bool): If True, create as a draft release. Defaults to False.

    Returns:
        str: JSON with the release URL and id on success, or an error.
    """
    import requests

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        return json.dumps({"error": "GITHUB_TOKEN environment variable is not set."})

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Create the release
    payload = {"tag_name": tag, "name": title, "body": body, "draft": draft}
    try:
        resp = requests.post(
            f"https://api.github.com/repos/{repo}/releases",
            headers=headers, json=payload, timeout=20,
        )
        if resp.status_code not in (200, 201):
            return json.dumps({"error": f"HTTP {resp.status_code}", "details": resp.text[:500]})
        release = resp.json()
        release_id = release["id"]
        release_url = release["html_url"]

        # Upload asset if provided
        asset_url = None
        if file_path:
            asset_path = Path(file_path)
            if asset_path.exists():
                upload_url = release["upload_url"].replace("{?name,label}", "")
                with open(asset_path, "rb") as f:
                    asset_headers = dict(headers)
                    asset_headers["Content-Type"] = "application/octet-stream"
                    ar = requests.post(
                        f"{upload_url}?name={asset_path.name}",
                        headers=asset_headers, data=f, timeout=120,
                    )
                    if ar.status_code in (200, 201):
                        asset_url = ar.json().get("browser_download_url")

        record = {
            "provider": "github", "repo": repo, "tag": tag,
            "url": release_url, "timestamp": time.time(),
        }
        _log_deployment(record)
        return json.dumps({
            "ok": True, "release_id": release_id,
            "url": release_url, "asset_url": asset_url,
        })
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def list_deployment_history(limit: int = 20) -> str:
    """
    Return the history of cloud deployments made by workflow agents.

    Args:
        limit (int): Maximum number of recent deployments to return. Defaults to 20.

    Returns:
        str: JSON array of deployment records ordered newest-first.
    """
    if not _DEPLOY_LOG_PATH.exists():
        return json.dumps([])
    try:
        lines = _DEPLOY_LOG_PATH.read_text().splitlines()
        records = []
        for line in reversed(lines):
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
            if len(records) >= limit:
                break
        return json.dumps(records, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def generate_static_site(content: str, title: str = "Generated Site",
                         output_dir: str = "WareHouse/static_site") -> str:
    """
    Generate a minimal static HTML site from Markdown or plain text content.
    Useful for quickly deploying documentation or reports to S3/GCS as a website.

    Args:
        content (str): Markdown or plain text content for the page body.
        title (str): Page title shown in browser tab and H1 heading. Defaults to 'Generated Site'.
        output_dir (str): Local directory where the site files are written. Defaults to 'WareHouse/static_site'.

    Returns:
        str: JSON with paths to generated files and a deployment hint.
    """
    try:
        import re
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        # Simple markdown-to-HTML conversion (headings, bold, lists, code)
        html_body = content
        html_body = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html_body, flags=re.MULTILINE)
        html_body = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html_body, flags=re.MULTILINE)
        html_body = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html_body, flags=re.MULTILINE)
        html_body = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html_body)
        html_body = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html_body)
        html_body = re.sub(r"`(.+?)`", r"<code>\1</code>", html_body)
        html_body = re.sub(r"^- (.+)$", r"<li>\1</li>", html_body, flags=re.MULTILINE)
        html_body = html_body.replace("\n\n", "</p><p>")

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.6; color: #222; }}
    h1,h2,h3 {{ color: #111; }} code {{ background:#f4f4f4; padding:2px 6px; border-radius:3px; }}
    li {{ margin: 4px 0; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p>{html_body}</p>
  <footer style="margin-top:40px;color:#888;font-size:0.85em;">Generated by DevAll &mdash; {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}</footer>
</body>
</html>"""

        index_path = out / "index.html"
        index_path.write_text(html)

        return json.dumps({
            "ok": True,
            "files": [str(index_path)],
            "output_dir": str(out),
            "hint": f"Upload '{out}/' to S3/GCS with static website hosting enabled. Use deploy_to_s3 or deploy_to_gcs for each file.",
        })
    except Exception as exc:
        return json.dumps({"error": str(exc)})
