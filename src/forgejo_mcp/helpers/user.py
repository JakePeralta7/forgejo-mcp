"""User and notification tools."""

from __future__ import annotations

from typing import Any

import httpx

from forgejo_mcp.client import list_page, pagination_params, request
from forgejo_mcp.server import READ_ONLY, forgejo_errors, get_client, mcp


@forgejo_errors
def do_get_user(client: httpx.Client, username: str) -> dict[str, Any]:
    return request(client, "GET", f"/users/{username}").json()


@forgejo_errors
def do_search_users(
    client: httpx.Client, q: str, limit: int = 10
) -> dict[str, Any]:
    params = pagination_params(limit=limit)
    params["q"] = q
    return list_page(client, "GET", "/users/search", params=params)


@forgejo_errors
def do_get_my_user(client: httpx.Client) -> dict[str, Any]:
    return request(client, "GET", "/user").json()


@forgejo_errors
def do_list_my_repos(
    client: httpx.Client, page: int | None = None, limit: int | None = None
) -> dict[str, Any]:
    return list_page(
        client, "GET", "/user/repos", params=pagination_params(page, limit)
    )


@forgejo_errors
def do_get_notifications(
    client: httpx.Client, page: int | None = None, limit: int | None = None
) -> dict[str, Any]:
    return list_page(
        client, "GET", "/notifications", params=pagination_params(page, limit)
    )


@forgejo_errors
def do_mark_notifications_read(client: httpx.Client) -> dict[str, Any]:
    # Forgejo's PUT /notifications has no per-thread endpoint: it marks
    # notifications read via query params (all=true applies to everything).
    resp = request(client, "PUT", "/notifications", params={"all": "true"})
    count = len(resp.json()) if resp.content else 0
    return {"marked_read": True, "count": count}


@mcp.tool(annotations=READ_ONLY)
def get_user(username: str) -> dict[str, Any]:
    """Get information about a user by username."""
    return do_get_user(get_client(), username)


@mcp.tool(annotations=READ_ONLY)
def search_users(q: str, limit: int = 10) -> dict[str, Any]:
    """Search for users matching ``q``. Returns ``{items, total_count}``."""
    return do_search_users(get_client(), q, limit)


@mcp.tool(annotations=READ_ONLY)
def get_my_user() -> dict[str, Any]:
    """Get information about the authenticated user."""
    return do_get_my_user(get_client())


@mcp.tool(annotations=READ_ONLY)
def list_my_repos(page: int | None = None, limit: int | None = None) -> dict[str, Any]:
    """List repositories owned by the authenticated user."""
    return do_list_my_repos(get_client(), page, limit)


@mcp.tool(annotations=READ_ONLY)
def get_notifications(page: int | None = None, limit: int | None = None) -> dict[str, Any]:
    """List notifications for the authenticated user."""
    return do_get_notifications(get_client(), page, limit)


@mcp.tool()
def mark_notifications_read() -> dict[str, Any]:
    """Mark all notification threads as read."""
    return do_mark_notifications_read(get_client())
