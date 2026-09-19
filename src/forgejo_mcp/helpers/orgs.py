"""Organization and team tools."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from forgejo_mcp.client import list_page, pagination_params
from forgejo_mcp.server import READ_ONLY, forgejo_errors, get_client, logger, mcp


@forgejo_errors
def do_list_user_orgs(client: httpx.Client, username: str) -> dict[str, Any]:
    return list_page(
        client, "GET", f"/users/{username}/orgs", params=pagination_params(limit=100)
    )


@forgejo_errors
def do_list_org_repos(
    client: httpx.Client, org: str, page: int | None = None, limit: int | None = None
) -> dict[str, Any]:
    return list_page(
        client, "GET", f"/orgs/{org}/repos", params=pagination_params(page, limit)
    )


@forgejo_errors
def do_list_org_members(
    client: httpx.Client, org: str, page: int | None = None, limit: int | None = None
) -> dict[str, Any]:
    return list_page(
        client, "GET", f"/orgs/{org}/members", params=pagination_params(page, limit)
    )


@forgejo_errors
def do_search_org_teams(
    client: httpx.Client,
    org: str,
    q: str | None = None,
    page: int | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    params = pagination_params(page, limit)
    if q:
        params["q"] = q
    return list_page(client, "GET", f"/orgs/{org}/teams/search", params=params)


@mcp.tool(annotations=READ_ONLY)
def list_user_orgs(username: str) -> dict[str, Any]:
    """List a user's organizations."""
    logger.debug("list_user_orgs", extra={"username": username})
    return do_list_user_orgs(get_client(), username)


@mcp.tool(annotations=READ_ONLY)
def list_org_repos(org: str, page: int | None = None, limit: int | None = None) -> dict[str, Any]:
    """List an organization's repositories."""
    logger.debug("list_org_repos", extra={"org": org, "page": page, "limit": limit})
    return do_list_org_repos(get_client(), org, page, limit)


@mcp.tool(annotations=READ_ONLY)
def list_org_members(org: str, page: int | None = None, limit: int | None = None) -> dict[str, Any]:
    """List an organization's members."""
    logger.debug("list_org_members", extra={"org": org, "page": page, "limit": limit})
    return do_list_org_members(get_client(), org, page, limit)


@mcp.tool(annotations=READ_ONLY)
def search_org_teams(
    org: str, q: str | None = None, page: int | None = None, limit: int | None = None
) -> dict[str, Any]:
    """Search teams in an organization by name (``q`` optional)."""
    logger.debug("search_org_teams", extra={"org": org, "query": q, "page": page, "limit": limit})
    return do_search_org_teams(get_client(), org, q, page, limit)