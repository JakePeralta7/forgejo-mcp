from unittest.mock import MagicMock

import pytest

import forgejo_mcp.server as server
from forgejo_mcp.helpers.actions import (
    do_dispatch_workflow,
    do_get_workflow_run,
    do_list_workflow_runs,
)


@pytest.fixture
def client():
    c = MagicMock()
    server.set_client(c)
    yield c
    server.set_client(None)


def json_response(client, payload, headers=None, status=200):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.headers = headers or {}
    resp.status_code = status
    client.request.return_value = resp
    return resp


class TestListWorkflowRuns:
    def test_filters(self, client):
        json_response(client, {"total_count": 2, "workflow_runs": [{"id": 1}, {"id": 2}]})
        result = do_list_workflow_runs(client, "owner", "repo", status="failure", event="push")
        kwargs = client.request.call_args.kwargs
        assert kwargs["params"]["status"] == "failure"
        assert kwargs["params"]["event"] == "push"
        assert client.request.call_args.args[1] == "/repos/owner/repo/actions/runs"
        assert len(result["items"]) == 2
        assert result["total_count"] == 2

    def test_bare_array_fallback(self, client):
        json_response(client, [{"id": 1}], headers={"x-total-count": "1"})
        result = do_list_workflow_runs(client, "owner", "repo")
        assert len(result["items"]) == 1
        assert result["total_count"] == 1


class TestGetWorkflowRun:
    def test_path(self, client):
        json_response(client, {"id": 7})
        result = do_get_workflow_run(client, "owner", "repo", 7)
        assert result["id"] == 7
        assert client.request.call_args.args[1] == "/repos/owner/repo/actions/runs/7"


class TestDispatchWorkflow:
    def test_dispatch(self, client):
        json_response(client, {}, status=204)
        result = do_dispatch_workflow(client, "owner", "repo", "ci.yml", "main", {"key": "v"})
        assert result["dispatched"] is True
        args, kwargs = client.request.call_args
        assert args[0] == "POST"
        assert args[1] == "/repos/owner/repo/actions/workflows/ci.yml/dispatches"
        assert kwargs["json"] == {"ref": "main", "inputs": {"key": "v"}}
