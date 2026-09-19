"""Issue and issue-comment tools."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from forgejo_mcp.client import list_page, pagination_params, request
from forgejo_mcp.server import READ_ONLY, READ_ONLY_MODE, forgejo_errors, get_client, logger, mcp


@forgejo_errors
def do_list_issues(
    client: httpx.Client,
    owner: str,
    repo: str,
    state: str | None = None,
    labels: str | None = None,
    page: int | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    params = pagination_params(page, limit)
    if state:
        params["state"] = state
    if labels:
        params["labels"] = labels
    return list_page(client, "GET", f"/repos/{owner}/{repo}/issues", params=params)


@forgejo_errors
def do_get_issue(client: httpx.Client, owner: str, repo: str, index: int) -> dict[str, Any]:
    return request(client, "GET", f"/repos/{owner}/{repo}/issues/{index}").json()


@forgejo_errors
def do_create_issue(
    client: httpx.Client,
    owner: str,
    repo: str,
    title: str,
    body: str | None = None,
    labels: list[int] | list[str] | None = None,
    assignees: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"title": title}
    if body:
        payload["body"] = body
    if labels:
        # Forgejo's CreateIssueOption.labels is []int64 (label IDs), so
        # accept either int IDs or numeric strings and coerce to int.
        payload["labels"] = [int(label) for label in labels]
    if assignees:
        payload["assignees"] = assignees
    return request(client, "POST", f"/repos/{owner}/{repo}/issues", json=payload).json()


@forgejo_errors
def do_update_issue(
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
        client, "PATCH", f"/repos/{owner}/{repo}/issues/{index}", json=payload
    ).json()


@forgejo_errors
def do_list_issue_comments(
    client: httpx.Client,
    owner: str,
    repo: str,
    index: int,
    page: int | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    return list_page(
        client,
        "GET",
        f"/repos/{owner}/{repo}/issues/{index}/comments",
        params=pagination_params(page, limit),
    )


@forgejo_errors
def do_create_issue_comment(
    client: httpx.Client, owner: str, repo: str, index: int, body: str
) -> dict[str, Any]:
    return request(
        client,
        "POST",
        f"/repos/{owner}/{repo}/issues/{index}/comments",
        json={"body": body},
    ).json()


@forgejo_errors
def do_edit_issue_comment(
    client: httpx.Client, owner: str, repo: str, index: int, comment_id: int, body: str
) -> dict[str, Any]:
    return request(
        client,
        "PATCH",
        f"/repos/{owner}/{repo}/issues/comments/{comment_id}",
        json={"body": body},
    ).json()


@forgejo_errors
def do_delete_issue_comment(
    client: httpx.Client, owner: str, repo: str, index: int, comment_id: int
) -> dict[str, Any]:
    resp = request(
        client, "DELETE", f"/repos/{owner}/{repo}/issues/comments/{comment_id}"
    )
    return {"deleted": True, "comment_id": comment_id, "status": resp.status_code}


@mcp.tool(annotations=READ_ONLY)
def list_issues(
    owner: str,
    repo: str,
    state: str | None = None,
    labels: str | None = None,
    page: int | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """List issues. ``state`` in open/closed/all; ``labels`` comma-separated names."""
    logger.debug("list_issues", extra={"owner": owner, "repo": repo, "state": state, "labels": labels, "page": page, "limit": limit})
    return do_list_issues(get_client(), owner, repo, state, labels, page, limit)


@mcp.tool(annotations=READ_ONLY)
def get_issue(owner: str, repo: str, index: int) -> dict[str, Any]:
    """Get an issue by its numeric index."""
    logger.debug("get_issue", extra={"owner": owner, "repo": repo, "index": index})
    return do_get_issue(get_client(), owner, repo, index)


def _register_create_issue():
    if READ_ONLY_MODE:
        logger.info("skipping_write_tool", extra={"tool": "create_issue", "reason": "read_only_mode"})
        return

    @mcp.tool()
    def create_issue(
        owner: str,
        repo: str,
        title: str,
        body: str | None = None,
        labels: list[int] | list[str] | None = None,
        assignees: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new issue. ``labels`` is a list of numeric label IDs."""
        logger.debug("create_issue", extra={"owner": owner, "repo": repo, "title": title})
        return do_create_issue(get_client(), owner, repo, title, body, labels, assignees)


_register_create_issue()


def _register_update_issue():
    if READ_ONLY_MODE:
        logger.info("skipping_write_tool", extra={"tool": "update_issue", "reason": "read_only_mode"})
        return

    @mcp.tool()
    def update_issue(
        owner: str,
        repo: str,
        index: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
    ) -> dict[str, Any]:
        """Update an issue's title, body, and/or state."""
        logger.debug("update_issue", extra={"owner": owner, "repo": repo, "index": index})
        return do_update_issue(get_client(), owner, repo, index, title, body, state)


_register_update_issue()


@mcp.tool(annotations=READ_ONLY)
def list_issue_comments(
    owner: str, repo: str, index: int, page: int | None = None, limit: int | None = None
) -> dict[str, Any]:
    """List comments on an issue or pull request."""
    logger.debug("list_issue_comments", extra={"owner": owner, "repo": repo, "index": index, "page": page, "limit": limit})
    return do_list_issue_comments(get_client(), owner, repo, index, page, limit)


def _register_create_issue_comment():
    if READ_ONLY_MODE:
        logger.info("skipping_write_tool", extra={"tool": "create_issue_comment", "reason": "read_only_mode"})
        return

    @mcp.tool()
    def create_issue_comment(owner: str, repo: str, index: int, body: str) -> dict[str, Any]:
        """Add a comment to an issue or pull request."""
        logger.debug("create_issue_comment", extra={"owner": owner, "repo": repo, "index": index})
        return do_create_issue_comment(get_client(), owner, repo, index, body)


_register_create_issue_comment()


def _register_edit_issue_comment():
    if READ_ONLY_MODE:
        logger.info("skipping_write_tool", extra={"tool": "edit_issue_comment", "reason": "read_only_mode"})
        return

    @mcp.tool()
    def edit_issue_comment(owner: str, repo: str, index: int, comment_id: int, body: str) -> dict[str, Any]:
        """Edit a comment on an issue or pull request."""
        logger.debug("edit_issue_comment", extra={"owner": owner, "repo": repo, "index": index, "comment_id": comment_id})
        return do_edit_issue_comment(get_client(), owner, repo, index, comment_id, body)


_register_edit_issue_comment()


def _register_delete_issue_comment():
    if READ_ONLY_MODE:
        logger.info("skipping_write_tool", extra={"tool": "delete_issue_comment", "reason": "read_only_mode"})
        return

    @mcp.tool()
    def delete_issue_comment(owner: str, repo: str, index: int, comment_id: int) -> dict[str, Any]:
        """Delete a comment on an issue or pull request."""
        logger.debug("delete_issue_comment", extra={"owner": owner, "repo": repo, "index": index, "comment_id": comment_id})
        return do_delete_issue_comment(get_client(), owner, repo, index, comment_id)


_register_delete_issue_comment()