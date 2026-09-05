"""Pull request and review tools."""

from __future__ import annotations

from typing import Any

import httpx

from forgejo_mcp.client import list_page, pagination_params, request
from forgejo_mcp.server import READ_ONLY, forgejo_errors, get_client, mcp


@forgejo_errors
def do_list_pull_requests(
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
        client, "GET", f"/repos/{owner}/{repo}/pulls", params=params
    )


@forgejo_errors
def do_get_pull_request(
    client: httpx.Client, owner: str, repo: str, index: int
) -> dict[str, Any]:
    return request(client, "GET", f"/repos/{owner}/{repo}/pulls/{index}").json()


@forgejo_errors
def do_create_pull_request(
    client: httpx.Client,
    owner: str,
    repo: str,
    title: str,
    head: str,
    base: str,
    body: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"title": title, "head": head, "base": base}
    if body:
        payload["body"] = body
    return request(client, "POST", f"/repos/{owner}/{repo}/pulls", json=payload).json()


@forgejo_errors
def do_update_pull_request(
    client: httpx.Client,
    owner: str,
    repo: str,
    index: int,
    title: str | None = None,
    body: str | None = None,
    state: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if title is not None:
        payload["title"] = title
    if body is not None:
        payload["body"] = body
    if state is not None:
        payload["state"] = state
    return request(
        client, "PATCH", f"/repos/{owner}/{repo}/pulls/{index}", json=payload
    ).json()


@forgejo_errors
def do_merge_pull_request(
    client: httpx.Client, owner: str, repo: str, index: int, method: str = "merge"
) -> dict[str, Any]:
    resp = request(
        client,
        "POST",
        f"/repos/{owner}/{repo}/pulls/{index}/merge",
        json={"Do": method},
    )
    # Forgejo returns 200 OK with an empty body on merge, so don't parse JSON.
    return {"merged": True, "status": resp.status_code}


@forgejo_errors
def do_list_pull_reviews(
    client: httpx.Client, owner: str, repo: str, index: int
) -> dict[str, Any]:
    return list_page(
        client, "GET", f"/repos/{owner}/{repo}/pulls/{index}/reviews", params=None
    )


@forgejo_errors
def do_get_pull_review(
    client: httpx.Client, owner: str, repo: str, index: int, review_id: int
) -> dict[str, Any]:
    return request(
        client, "GET", f"/repos/{owner}/{repo}/pulls/{index}/reviews/{review_id}"
    ).json()


@forgejo_errors
def do_list_pull_review_comments(
    client: httpx.Client, owner: str, repo: str, index: int, review_id: int
) -> dict[str, Any]:
    return list_page(
        client,
        "GET",
        f"/repos/{owner}/{repo}/pulls/{index}/reviews/{review_id}/comments",
        params=None,
    )


@forgejo_errors
def do_create_pull_review(
    client: httpx.Client,
    owner: str,
    repo: str,
    index: int,
    event: str,
    body: str | None = None,
    comments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"event": event}
    if body:
        payload["body"] = body
    if comments:
        payload["comments"] = comments
    return request(
        client, "POST", f"/repos/{owner}/{repo}/pulls/{index}/reviews", json=payload
    ).json()


@mcp.tool(annotations=READ_ONLY)
def list_pull_requests(
    owner: str,
    repo: str,
    state: str | None = None,
    page: int | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """List pull requests. ``state`` in open/closed/all."""
    return do_list_pull_requests(get_client(), owner, repo, state, page, limit)


@mcp.tool(annotations=READ_ONLY)
def get_pull_request(owner: str, repo: str, index: int) -> dict[str, Any]:
    """Get a pull request by its numeric index."""
    return do_get_pull_request(get_client(), owner, repo, index)


@mcp.tool()
def create_pull_request(
    owner: str, repo: str, title: str, head: str, base: str, body: str | None = None
) -> dict[str, Any]:
    """Create a pull request. ``head`` is the source branch, ``base`` the target."""
    return do_create_pull_request(get_client(), owner, repo, title, head, base, body)


@mcp.tool()
def update_pull_request(
    owner: str,
    repo: str,
    index: int,
    title: str | None = None,
    body: str | None = None,
    state: str | None = None,
) -> dict[str, Any]:
    """Update a pull request's title, body, and/or state."""
    return do_update_pull_request(get_client(), owner, repo, index, title, body, state)


@mcp.tool()
def merge_pull_request(
    owner: str, repo: str, index: int, method: str = "merge"
) -> dict[str, Any]:
    """Merge a pull request. ``method`` in merge/rebase/rebase-merge/squash/fast-forward-only/manually-merged."""
    return do_merge_pull_request(get_client(), owner, repo, index, method)


@mcp.tool(annotations=READ_ONLY)
def list_pull_reviews(owner: str, repo: str, index: int) -> dict[str, Any]:
    """List reviews on a pull request."""
    return do_list_pull_reviews(get_client(), owner, repo, index)


@mcp.tool(annotations=READ_ONLY)
def get_pull_review(owner: str, repo: str, index: int, review_id: int) -> dict[str, Any]:
    """Get a specific review on a pull request."""
    return do_get_pull_review(get_client(), owner, repo, index, review_id)


@mcp.tool(annotations=READ_ONLY)
def list_pull_review_comments(
    owner: str, repo: str, index: int, review_id: int
) -> dict[str, Any]:
    """List comments on a specific pull request review."""
    return do_list_pull_review_comments(get_client(), owner, repo, index, review_id)


@mcp.tool()
def create_pull_review(
    owner: str,
    repo: str,
    index: int,
    event: str,
    body: str | None = None,
    comments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Submit a pull request review. ``event`` in APPROVED/REQUEST_CHANGES/COMMENT."""
    return do_create_pull_review(get_client(), owner, repo, index, event, body, comments)
