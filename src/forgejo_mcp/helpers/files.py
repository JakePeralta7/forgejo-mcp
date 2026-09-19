"""File content and commit tools."""

from __future__ import annotations

import base64 as b64
import logging
from typing import Any

import httpx

from forgejo_mcp.client import list_page, pagination_params, request
from forgejo_mcp.server import READ_ONLY, READ_ONLY_MODE, forgejo_errors, get_client, logger, mcp


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


@forgejo_errors
def do_list_repo_files(
    client: httpx.Client,
    owner: str,
    repo: str,
    path: str = "/",
    depth: int = -1,
    ref: str | None = None,
) -> dict[str, Any]:
    """List files in a repository using the Git tree API.
    
    Args:
        client: HTTP client
        owner: Repository owner
        repo: Repository name
        path: Starting path (default: "/", root). Must start with "/".
        depth: Maximum depth to traverse (0-based: 0=starting dir only, 
               1=one level deeper, -1=unlimited). Default: -1.
        ref: Branch, tag, or commit SHA (default: repository's default branch)
    """
    if not path.startswith("/"):
        raise ValueError("path must start with '/'")
    if depth < -1:
        raise ValueError("depth must be >= -1")
    
    # Resolve the commit SHA
    if ref:
        tree_sha = ref
    else:
        repo_info = request(client, "GET", f"/repos/{owner}/{repo}").json()
        tree_sha = repo_info.get("default_branch", "main")
    
    # Fetch the tree recursively
    resp = request(
        client,
        "GET",
        f"/repos/{owner}/{repo}/git/trees/{tree_sha}",
        params={"recursive": "1", "per_page": 1000},
    )
    tree_data = resp.json()
    
    entries = tree_data.get("tree", [])
    if not entries:
        return {"items": [], "total_count": 0}
    
    # Normalize path for prefix matching
    norm_path = path.lstrip("/")
    if norm_path and not norm_path.endswith("/"):
        norm_path += "/"
    
    base_depth = norm_path.count("/")
    
    filtered: list[dict[str, Any]] = []
    for entry in entries:
        entry_path = entry.get("path", "")
        if norm_path and not entry_path.startswith(norm_path):
            continue
        if entry_path == norm_path.rstrip("/"):
            continue  # skip the directory itself
        
        entry_depth = entry_path.count("/") - base_depth
        if depth >= 0 and entry_depth > depth:
            continue
        
        filtered.append({
            "path": entry_path,
            "type": entry.get("type"),
            "sha": entry.get("sha"),
            "size": entry.get("size"),
            "mode": entry.get("mode"),
        })
    
    return {"items": filtered, "total_count": len(filtered)}


@mcp.tool(annotations=READ_ONLY)
def get_file_content(owner: str, repo: str, filepath: str, ref: str | None = None) -> dict[str, Any]:
    """Read a file. UTF-8 content returns as text; anything else as base64."""
    logger.debug("get_file_content", extra={"owner": owner, "repo": repo, "filepath": filepath, "ref": ref})
    return do_get_file_content(get_client(), owner, repo, filepath, ref)


@mcp.tool(annotations=READ_ONLY)
def list_repo_commits(
    owner: str, repo: str, branch: str | None = None, page: int | None = None, limit: int | None = None
) -> dict[str, Any]:
    """List commits in a repository (``branch`` optional)."""
    logger.debug("list_repo_commits", extra={"owner": owner, "repo": repo, "branch": branch, "page": page, "limit": limit})
    return do_list_repo_commits(get_client(), owner, repo, branch, page, limit)


@mcp.tool(annotations=READ_ONLY)
def get_commit(owner: str, repo: str, sha: str) -> dict[str, Any]:
    """Get a single commit by SHA."""
    logger.debug("get_commit", extra={"owner": owner, "repo": repo, "sha": sha})
    return do_get_commit(get_client(), owner, repo, sha)


@mcp.tool(annotations=READ_ONLY)
def list_repo_files(
    owner: str,
    repo: str,
    path: str = "/",
    depth: int = -1,
    ref: str | None = None,
) -> dict[str, Any]:
    """List files in a repository.
    
    Args:
        owner: Repository owner
        repo: Repository name
        path: Starting path (default: "/", root). Must start with "/".
        depth: Maximum depth to traverse (0-based: 0=starting dir only,
               1=one level deeper, -1=unlimited). Default: -1.
        ref: Branch, tag, or commit SHA (default: repository's default branch)
    """
    logger.debug("list_repo_files", extra={"owner": owner, "repo": repo, "path": path, "depth": depth, "ref": ref})
    return do_list_repo_files(get_client(), owner, repo, path, depth, ref)


def _register_create_file():
    if READ_ONLY_MODE:
        logger.info("skipping_write_tool", extra={"tool": "create_file", "reason": "read_only_mode"})
        return

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
        logger.debug("create_file", extra={"owner": owner, "repo": repo, "filepath": filepath, "branch": branch})
        return do_create_file(get_client(), owner, repo, filepath, content, message, branch, base64)


_register_create_file()


def _register_update_file():
    if READ_ONLY_MODE:
        logger.info("skipping_write_tool", extra={"tool": "update_file", "reason": "read_only_mode"})
        return

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
        logger.debug("update_file", extra={"owner": owner, "repo": repo, "filepath": filepath, "branch": branch})
        return do_update_file(get_client(), owner, repo, filepath, content, message, branch, sha, base64)


_register_update_file()


def _register_delete_file():
    if READ_ONLY_MODE:
        logger.info("skipping_write_tool", extra={"tool": "delete_file", "reason": "read_only_mode"})
        return

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
        logger.debug("delete_file", extra={"owner": owner, "repo": repo, "filepath": filepath, "branch": branch})
        return do_delete_file(get_client(), owner, repo, filepath, message, branch, sha)


_register_delete_file()