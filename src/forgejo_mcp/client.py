"""The only place forgejo-mcp talks HTTP.

Provides a small, pagination-aware wrapper around an `httpx.Client` so domain
helpers never touch httpx directly. All paths are joined onto
`{FORGEJO_URL}/api/v1`.
"""

from __future__ import annotations

from typing import Any

import httpx

MAX_PAGE_LIMIT = 100

_DEFAULT_LIMITS = httpx.Limits(
    max_connections=20,
    max_keepalive_connections=5,
    keepalive_expiry=30.0,
)


def create_transport(limits: httpx.Limits | None = None) -> httpx.BaseTransport:
    """Create an HTTP transport with connection pooling configuration."""
    return httpx.HTTPTransport(limits=limits or _DEFAULT_LIMITS)


def request(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
) -> httpx.Response:
    """Send a request against the Forgejo REST API and raise on non-2xx.

    ``path`` is relative to ``/api/v1`` (leading slash optional). Non-2xx
    responses raise :class:`httpx.HTTPStatusError`, which the ``@forgejo_errors``
    decorator converts into a short ``RuntimeError``.
    """
    url = path if path.startswith("/") else f"/{path}"
    resp = client.request(method, url, params=params, json=json)
    resp.raise_for_status()
    return resp


def pagination_params(
    page: int | None = None, limit: int | None = None
) -> dict[str, Any]:
    """Build ``page``/``limit`` query params, clamping ``limit`` to a sane max."""
    params: dict[str, Any] = {}
    if page is not None:
        if page < 1:
            raise ValueError("page must be >= 1")
        params["page"] = page
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        params["limit"] = min(limit, MAX_PAGE_LIMIT)
    return params


def list_page(
    client: httpx.Client, method: str, path: str, *, params: dict[str, Any] | None
) -> dict[str, Any]:
    """Fetch one page and wrap it as the standard envelope.

    Returns ``{"items": [...], "total_count": n}`` where ``n`` comes from the
    ``x-total-count`` response header (0 when absent).
    """
    resp = request(client, method, path, params=params)
    total = int(resp.headers.get("x-total-count", 0) or 0)
    return {"items": resp.json(), "total_count": total}
