"""Pull request and review tools."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from forgejo_mcp.client import list_page, pagination_params, request
from forgejo_mcp.server import READ_ONLY, READ_ONLY_MODE, forgejo_errors, get_client, logger, mcp


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
    logger.debug("list_pull_requests", extra={"owner": owner, "repo": repo, "state": state, "page": page, "limit": limit})
    return do_list_pull_requests(get_client(), owner, repo, state, page, limit)


@mcp.tool(annotations=READ_ONLY)
def get_pull_request(owner: str, repo: str, index: int) -> dict[str, Any]:
    """Get a pull request by its numeric index."""
    logger.debug("get_pull_request", extra={"owner": owner, "repo": repo, "index": index})
    return do_get_pull_request(get_client(), owner, repo, index)


def _register_create_pull_request():
    if READ_ONLY_MODE:
        logger.info("skipping_write_tool", extra={"tool": "create_pull_request", "reason": "read_only_mode"})
        return

    @mcp.tool()
    def create_pull_request(
        owner: str, repo: str, title: str, head: str, base: str, body: str | None = None
    ) -> dict[str, Any]:
        """Create a pull request. ``head`` is the source branch, ``base`` the target."""
        logger.debug("create_pull_request", extra={"owner": owner, "repo": repo, "title": title, "head": head, "base": base})
        return do_create_pull_request(get_client(), owner, repo, title, head, base, body)


_register_create_pull_request()


def _register_update_pull_request():
    if READ_ONLY_MODE:
        logger.info("skipping_write_tool", extra={"tool": "update_pull_request", "reason": "read_only_mode"})
        return

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
        logger.debug("update_pull_request", extra={"owner": owner, "repo": repo, "index": index})
        return do_update_pull_request(get_client(), owner, repo, index, title, body, state)


_register_update_pull_request()


def _register_merge_pull_request():
    if READ_ONLY_MODE:
        logger.info("skipping_write_tool", extra={"tool": "merge_pull_request", "reason": "read_only_mode"})
        return

    @mcp.tool()
    def merge_pull_request(
        owner: str, repo: str, index: int, method: str = "merge"
    ) -> dict[str, Any]:
        """Merge a pull request. ``method`` in merge/rebase/rebase-merge/squash/fast-forward-only/manually-merged."""
        logger.debug("merge_pull_request", extra={"owner": owner, "repo": repo, "index": index, "method": method})
        return do_merge_pull_request(get_client(), owner, repo, index, method)


_register_merge_pull_request()


@mcp.tool(annotations=READ_ONLY)
def list_pull_reviews(owner: str, repo: str, index: int) -> dict[str, Any]:
    """List reviews on a pull request."""
    logger.debug("list_pull_reviews", extra={"owner": owner, "repo": repo, "index": index})
    return do_list_pull_reviews(get_client(), owner, repo, index)


@mcp.tool(annotations=READ_ONLY)
def get_pull_review(owner: str, repo: str, index: int, review_id: int) -> dict[str, Any]:
    """Get a specific review on a pull request."""
    logger.debug("get_pull_review", extra={"owner": owner, "repo": repo, "index": index, "review_id": review_id})
    return do_get_pull_review(get_client(), owner, repo, index, review_id)


@mcp.tool(annotations=READ_ONLY)
def list_pull_review_comments(
    owner: str, repo: str, index: int, review_id: int
) -> dict[str, Any]:
    """List comments on a specific pull request review."""
    logger.debug("list_pull_review_comments", extra={"owner": owner, "repo": repo, "index": index, "review_id": review_id})
    return do_list_pull_review_comments(get_client(), owner, repo, index, review_id)


def _register_create_pull_review():
    if READ_ONLY_MODE:
        logger.info("skipping_write_tool", extra={"tool": "create_pull_review", "reason": "read_only_mode"})
        return

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
        logger.debug("create_pull_review", extra={"owner": owner, "repo": repo, "index": index, "event": event})
        return do_create_pull_review(get_client(), owner, repo, index, event, body, comments)


_register_create_pull_review()