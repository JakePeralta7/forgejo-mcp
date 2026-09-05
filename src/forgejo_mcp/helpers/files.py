"""File content and commit tools."""

from __future__ import annotations

import base64 as b64
from typing import Any

import httpx

from forgejo_mcp.client import list_page, pagination_params, request
from forgejo_mcp.server import READ_ONLY, forgejo_errors, get_client, mcp


@forgejo_errors
def do_get_file_content(
    client: httpx.Client, owner: str, repo: str, filepath: str, ref: str | None = None
) -> dict[str, Any]:
    content = request(
        client,
        "GET",
        f"/repos/{owner}/{repo}/contents/{filepath}",
        params={"ref": ref} if ref else None,
    ).json()
    encoding = content.get("encoding")
    if encoding == "base64":
        raw = b64.b64decode(content.get("content", "") or "")
    else:
        raw = (content.get("content") or "").encode("utf-8")
    sha: str = content.get("sha") or ""
    try:
        text = raw.decode("utf-8")
        return {"encoding": "utf-8", "size": len(raw), "text": text, "sha": sha}
    except UnicodeDecodeError:
        return {
            "encoding": "base64",
            "size": len(raw),
            "base64": b64.b64encode(raw).decode("ascii"),
            "sha": sha,
        }


@forgejo_errors
def do_list_repo_commits(
    client: httpx.Client,
    owner: str,
    repo: str,
    branch: str | None = None,
    page: int | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    params = pagination_params(page, limit)
    if branch:
        params["sha"] = branch
    return list_page(client, "GET", f"/repos/{owner}/{repo}/commits", params=params)


@forgejo_errors
def do_get_commit(client: httpx.Client, owner: str, repo: str, sha: str) -> dict[str, Any]:
    return request(client, "GET", f"/repos/{owner}/{repo}/git/commits/{sha}").json()


@forgejo_errors
def do_create_file(
    client: httpx.Client,
    owner: str,
    repo: str,
    filepath: str,
    content: str,
    message: str,
    branch: str | None = None,
    base64: bool = False,
) -> dict[str, Any]:
    data = b64.b64decode(content, validate=True) if base64 else content.encode("utf-8")
    body: dict[str, Any] = {
        "content": b64.b64encode(data).decode("ascii"),
        "message": message,
    }
    if branch:
        body["branch"] = branch
    return request(
        client, "POST", f"/repos/{owner}/{repo}/contents/{filepath}", json=body
    ).json()


@forgejo_errors
def do_update_file(
    client: httpx.Client,
    owner: str,
    repo: str,
    filepath: str,
    content: str,
    message: str,
    branch: str | None = None,
    sha: str | None = None,
    base64: bool = False,
) -> dict[str, Any]:
    data = b64.b64decode(content, validate=True) if base64 else content.encode("utf-8")
    body: dict[str, Any] = {
        "content": b64.b64encode(data).decode("ascii"),
        "message": message,
    }
    if branch:
        body["branch"] = branch
    if sha:
        body["sha"] = sha
    return request(
        client, "PUT", f"/repos/{owner}/{repo}/contents/{filepath}", json=body
    ).json()


@forgejo_errors
def do_delete_file(
    client: httpx.Client,
    owner: str,
    repo: str,
    filepath: str,
    message: str,
    branch: str | None = None,
    sha: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"message": message}
    if branch:
        body["branch"] = branch
    if sha:
        body["sha"] = sha
    return request(
        client, "DELETE", f"/repos/{owner}/{repo}/contents/{filepath}", json=body
    ).json()


@mcp.tool(annotations=READ_ONLY)
def get_file_content(owner: str, repo: str, filepath: str, ref: str | None = None) -> dict[str, Any]:
    """Read a file. UTF-8 content returns as text; anything else as base64."""
    return do_get_file_content(get_client(), owner, repo, filepath, ref)


@mcp.tool(annotations=READ_ONLY)
def list_repo_commits(
    owner: str, repo: str, branch: str | None = None, page: int | None = None, limit: int | None = None
) -> dict[str, Any]:
    """List commits in a repository (``branch`` optional)."""
    return do_list_repo_commits(get_client(), owner, repo, branch, page, limit)


@mcp.tool(annotations=READ_ONLY)
def get_commit(owner: str, repo: str, sha: str) -> dict[str, Any]:
    """Get a single commit by SHA."""
    return do_get_commit(get_client(), owner, repo, sha)


@mcp.tool()
def create_file(
    owner: str,
    repo: str,
    filepath: str,
    content: str,
    message: str,
    branch: str | None = None,
    base64: bool = False,
) -> dict[str, Any]:
    """Create a file. Set ``base64=true`` when ``content`` is base64-encoded."""
    return do_create_file(get_client(), owner, repo, filepath, content, message, branch, base64)


@mcp.tool()
def update_file(
    owner: str,
    repo: str,
    filepath: str,
    content: str,
    message: str,
    branch: str | None = None,
    sha: str | None = None,
    base64: bool = False,
) -> dict[str, Any]:
    """Update an existing file. ``sha`` is the current file blob SHA."""
    return do_update_file(get_client(), owner, repo, filepath, content, message, branch, sha, base64)


@mcp.tool()
def delete_file(
    owner: str,
    repo: str,
    filepath: str,
    message: str,
    branch: str | None = None,
    sha: str | None = None,
) -> dict[str, Any]:
    """Delete a file."""
    return do_delete_file(get_client(), owner, repo, filepath, message, branch, sha)
