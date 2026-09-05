"""Repository, branch, label, milestone, and topic tools."""

from __future__ import annotations

from typing import Any

import httpx

from forgejo_mcp.client import list_page, pagination_params, request
from forgejo_mcp.server import READ_ONLY, forgejo_errors, get_client, mcp


@forgejo_errors
def do_get_repo(client: httpx.Client, owner: str, repo: str) -> dict[str, Any]:
    return request(client, "GET", f"/repos/{owner}/{repo}").json()


@forgejo_errors
def do_list_repos(
    client: httpx.Client, owner: str, page: int | None = None, limit: int | None = None
) -> dict[str, Any]:
    return list_page(
        client, "GET", f"/users/{owner}/repos", params=pagination_params(page, limit)
    )


@forgejo_errors
def do_search_repos(
    client: httpx.Client, q: str, page: int | None = None, limit: int | None = None
) -> dict[str, Any]:
    params = pagination_params(page, limit)
    params["q"] = q
    return list_page(client, "GET", "/repos/search", params=params)


@forgejo_errors
def do_create_repo(
    client: httpx.Client,
    name: str,
    private: bool = False,
    description: str | None = None,
    auto_init: bool = False,
) -> dict[str, Any]:
    body: dict[str, Any] = {"name": name, "private": private, "auto_init": auto_init}
    if description:
        body["description"] = description
    return request(client, "POST", "/user/repos", json=body).json()


@forgejo_errors
def do_fork_repo(client: httpx.Client, owner: str, repo: str) -> dict[str, Any]:
    return request(client, "POST", f"/repos/{owner}/{repo}/forks").json()


@forgejo_errors
def do_delete_repo(client: httpx.Client, owner: str, repo: str) -> dict[str, Any]:
    resp = request(client, "DELETE", f"/repos/{owner}/{repo}")
    return {"deleted": True, "owner": owner, "repo": repo, "status": resp.status_code}


@forgejo_errors
def do_list_branches(
    client: httpx.Client, owner: str, repo: str, page: int | None = None, limit: int | None = None
) -> dict[str, Any]:
    return list_page(
        client,
        "GET",
        f"/repos/{owner}/{repo}/branches",
        params=pagination_params(page, limit),
    )


@forgejo_errors
def do_create_branch(
    client: httpx.Client, owner: str, repo: str, new_branch: str, old_ref: str
) -> dict[str, Any]:
    return request(
        client,
        "POST",
        f"/repos/{owner}/{repo}/branches",
        json={"new_branch_name": new_branch, "old_ref_name": old_ref},
    ).json()


@forgejo_errors
def do_delete_branch(client: httpx.Client, owner: str, repo: str, branch: str) -> dict[str, Any]:
    resp = request(client, "DELETE", f"/repos/{owner}/{repo}/branches/{branch}")
    return {"deleted": True, "branch": branch, "status": resp.status_code}


@forgejo_errors
def do_list_labels(
    client: httpx.Client, owner: str, repo: str, page: int | None = None, limit: int | None = None
) -> dict[str, Any]:
    return list_page(
        client,
        "GET",
        f"/repos/{owner}/{repo}/labels",
        params=pagination_params(page, limit),
    )


@forgejo_errors
def do_create_label(
    client: httpx.Client, owner: str, repo: str, name: str, color: str
) -> dict[str, Any]:
    return request(
        client, "POST", f"/repos/{owner}/{repo}/labels", json={"name": name, "color": color}
    ).json()


@forgejo_errors
def do_list_milestones(
    client: httpx.Client,
    owner: str,
    repo: str,
    state: str | None = None,
    page: int | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    params = pagination_params(page, limit)
    if state:
        params["state"] = state
    return list_page(
        client, "GET", f"/repos/{owner}/{repo}/milestones", params=params
    )


@forgejo_errors
def do_create_milestone(
    client: httpx.Client,
    owner: str,
    repo: str,
    title: str,
    description: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"title": title}
    if description:
        body["description"] = description
    return request(
        client, "POST", f"/repos/{owner}/{repo}/milestones", json=body
    ).json()


@forgejo_errors
def do_list_repo_topics(client: httpx.Client, owner: str, repo: str) -> dict[str, Any]:
    resp = request(client, "GET", f"/repos/{owner}/{repo}/topics")
    return {"topics": (resp.json() or {}).get("topics", [])}


@mcp.tool(annotations=READ_ONLY)
def get_repo(owner: str, repo: str) -> dict[str, Any]:
    """Get a repository by owner and name."""
    return do_get_repo(get_client(), owner, repo)


@mcp.tool(annotations=READ_ONLY)
def list_repos(owner: str, page: int | None = None, limit: int | None = None) -> dict[str, Any]:
    """List repositories owned by ``owner``."""
    return do_list_repos(get_client(), owner, page, limit)


@mcp.tool(annotations=READ_ONLY)
def search_repos(q: str, page: int | None = None, limit: int | None = None) -> dict[str, Any]:
    """Search for repositories matching ``q``."""
    return do_search_repos(get_client(), q, page, limit)


@mcp.tool()
def create_repo(
    name: str, private: bool = False, description: str | None = None, auto_init: bool = False
) -> dict[str, Any]:
    """Create a repository owned by the authenticated user."""
    return do_create_repo(get_client(), name, private, description, auto_init)


@mcp.tool()
def fork_repo(owner: str, repo: str) -> dict[str, Any]:
    """Fork a repository into the authenticated user's account."""
    return do_fork_repo(get_client(), owner, repo)


@mcp.tool()
def delete_repo(owner: str, repo: str) -> dict[str, Any]:
    """Delete a repository."""
    return do_delete_repo(get_client(), owner, repo)


@mcp.tool(annotations=READ_ONLY)
def list_branches(owner: str, repo: str, page: int | None = None, limit: int | None = None) -> dict[str, Any]:
    """List branches in a repository."""
    return do_list_branches(get_client(), owner, repo, page, limit)


@mcp.tool()
def create_branch(owner: str, repo: str, new_branch: str, old_ref: str) -> dict[str, Any]:
    """Create a branch named ``new_branch`` from ``old_ref``."""
    return do_create_branch(get_client(), owner, repo, new_branch, old_ref)


@mcp.tool()
def delete_branch(owner: str, repo: str, branch: str) -> dict[str, Any]:
    """Delete a branch."""
    return do_delete_branch(get_client(), owner, repo, branch)


@mcp.tool(annotations=READ_ONLY)
def list_labels(owner: str, repo: str, page: int | None = None, limit: int | None = None) -> dict[str, Any]:
    """List issue labels in a repository."""
    return do_list_labels(get_client(), owner, repo, page, limit)


@mcp.tool()
def create_label(owner: str, repo: str, name: str, color: str) -> dict[str, Any]:
    """Create a label. ``color`` is a hex string like ``#ff0000``."""
    return do_create_label(get_client(), owner, repo, name, color)


@mcp.tool(annotations=READ_ONLY)
def list_milestones(
    owner: str, repo: str, state: str | None = None, page: int | None = None, limit: int | None = None
) -> dict[str, Any]:
    """List milestones in a repository (``state``: open/closed/all)."""
    return do_list_milestones(get_client(), owner, repo, state, page, limit)


@mcp.tool()
def create_milestone(owner: str, repo: str, title: str, description: str | None = None) -> dict[str, Any]:
    """Create a milestone."""
    return do_create_milestone(get_client(), owner, repo, title, description)


@mcp.tool(annotations=READ_ONLY)
def list_repo_topics(owner: str, repo: str) -> dict[str, Any]:
    """List the topics of a repository."""
    return do_list_repo_topics(get_client(), owner, repo)
