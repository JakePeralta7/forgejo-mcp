"""Forgejo Actions workflow-run tools."""

from __future__ import annotations

from typing import Any

import httpx

from forgejo_mcp.client import pagination_params, request
from forgejo_mcp.server import READ_ONLY, forgejo_errors, get_client, mcp


@forgejo_errors
def do_list_workflow_runs(
    client: httpx.Client,
    owner: str,
    repo: str,
    status: str | None = None,
    event: str | None = None,
    page: int | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    params = pagination_params(page, limit)
    if status:
        params["status"] = status
    if event:
        params["event"] = event
    resp = request(
        client, "GET", f"/repos/{owner}/{repo}/actions/runs", params=params
    )
    # Forgejo mirrors GitHub's envelope: {"total_count": n, "workflow_runs": [...]}
    data = resp.json()
    items = data.get("workflow_runs", []) if isinstance(data, dict) else data
    return {"items": items, "total_count": data.get("total_count", 0) if isinstance(data, dict) else len(items)}


@forgejo_errors
def do_get_workflow_run(
    client: httpx.Client, owner: str, repo: str, run_id: int
) -> dict[str, Any]:
    return request(
        client, "GET", f"/repos/{owner}/{repo}/actions/runs/{run_id}"
    ).json()


@forgejo_errors
def do_dispatch_workflow(
    client: httpx.Client,
    owner: str,
    repo: str,
    workflow_id: str,
    ref: str,
    inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"ref": ref}
    if inputs:
        payload["inputs"] = inputs
    resp = request(
        client,
        "POST",
        f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches",
        json=payload,
    )
    return {"dispatched": True, "status": resp.status_code}


@mcp.tool(annotations=READ_ONLY)
def list_workflow_runs(
    owner: str,
    repo: str,
    status: str | None = None,
    event: str | None = None,
    page: int | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """List Actions workflow runs. Optionally filter by ``status``/``event``."""
    return do_list_workflow_runs(get_client(), owner, repo, status, event, page, limit)


@mcp.tool(annotations=READ_ONLY)
def get_workflow_run(owner: str, repo: str, run_id: int) -> dict[str, Any]:
    """Get a single Actions workflow run by ID."""
    return do_get_workflow_run(get_client(), owner, repo, run_id)


@mcp.tool()
def dispatch_workflow(
    owner: str,
    repo: str,
    workflow_id: str,
    ref: str,
    inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Trigger a workflow run via the ``workflow_dispatch`` event."""
    return do_dispatch_workflow(get_client(), owner, repo, workflow_id, ref, inputs)
