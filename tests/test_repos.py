from unittest.mock import MagicMock

import pytest

import forgejo_mcp.server as server
from forgejo_mcp.helpers.repos import (
    do_create_branch,
    do_create_label,
    do_create_milestone,
    do_create_repo,
    do_delete_branch,
    do_delete_repo,
    do_fork_repo,
    do_get_repo,
    do_list_branches,
    do_list_labels,
    do_list_milestones,
    do_list_repo_topics,
    do_list_repos,
    do_search_repos,
)
from forgejo_mcp.server import forgejo_errors


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


class TestGetRepo:
    def test_path(self, client):
        json_response(client, {"name": "r"})
        result = do_get_repo(client, "owner", "repo")
        assert result["name"] == "r"
        assert client.request.call_args.args[1] == "/repos/owner/repo"


class TestListRepos:
    def test_paginated(self, client):
        json_response(client, [{"name": "r"}], headers={"x-total-count": "2"})
        result = do_list_repos(client, "owner", page=1, limit=25)
        assert result["total_count"] == 2
        kwargs = client.request.call_args.kwargs
        assert kwargs["params"] == {"page": 1, "limit": 25}


class TestSearchRepos:
    def test_query_param(self, client):
        json_response(client, [{"name": "r"}], headers={"x-total-count": "0"})
        do_search_repos(client, "query", limit=10)
        kwargs = client.request.call_args.kwargs
        assert kwargs["params"]["q"] == "query"


class TestCreateRepo:
    def test_body(self, client):
        json_response(client, {"name": "new"}, status=201)
        result = do_create_repo(client, "new", private=True, description="desc")
        assert result["name"] == "new"
        args, kwargs = client.request.call_args
        assert args[0] == "POST"
        assert args[1] == "/user/repos"
        assert kwargs["json"]["name"] == "new"
        assert kwargs["json"]["private"] is True


class TestForkRepo:
    def test_path(self, client):
        json_response(client, {"name": "fork"})
        do_fork_repo(client, "owner", "repo")
        args, kwargs = client.request.call_args
        assert args[0] == "POST"
        assert args[1] == "/repos/owner/repo/forks"


class TestDeleteRepo:
    def test_path(self, client):
        json_response(client, {}, status=204)
        result = do_delete_repo(client, "owner", "repo")
        assert result["deleted"] is True
        args, kwargs = client.request.call_args
        assert args[0] == "DELETE"
        assert args[1] == "/repos/owner/repo"


class TestBranches:
    def test_list(self, client):
        json_response(client, [{"name": "main"}], headers={"x-total-count": "1"})
        result = do_list_branches(client, "owner", "repo")
        assert result["items"][0]["name"] == "main"

    def test_create(self, client):
        json_response(client, {"name": "feature"}, status=201)
        do_create_branch(client, "owner", "repo", "feature", "main")
        kwargs = client.request.call_args.kwargs
        assert kwargs["json"] == {"new_branch_name": "feature", "old_ref_name": "main"}

    def test_delete(self, client):
        json_response(client, {}, status=204)
        result = do_delete_branch(client, "owner", "repo", "feature")
        assert result["deleted"] is True
        assert client.request.call_args.args[1] == "/repos/owner/repo/branches/feature"


class TestLabels:
    def test_list(self, client):
        json_response(client, [{"name": "bug"}], headers={"x-total-count": "1"})
        result = do_list_labels(client, "owner", "repo")
        assert result["items"][0]["name"] == "bug"

    def test_create(self, client):
        json_response(client, {"name": "bug"}, status=201)
        do_create_label(client, "owner", "repo", "bug", "#ff0000")
        kwargs = client.request.call_args.kwargs
        assert kwargs["json"] == {"name": "bug", "color": "#ff0000"}


class TestMilestones:
    def test_list_with_state(self, client):
        json_response(client, [{"title": "m"}], headers={"x-total-count": "1"})
        do_list_milestones(client, "owner", "repo", state="closed")
        assert client.request.call_args.kwargs["params"]["state"] == "closed"

    def test_create(self, client):
        json_response(client, {"title": "m"}, status=201)
        do_create_milestone(client, "owner", "repo", "m", "d")
        kwargs = client.request.call_args.kwargs
        assert kwargs["json"] == {"title": "m", "description": "d"}


class TestListRepoTopics:
    def test_shape(self, client):
        json_response(client, {"topics": ["go", "mcp"]})
        result = do_list_repo_topics(client, "owner", "repo")
        assert result == {"topics": ["go", "mcp"]}


def test_error_wrapping():
    c = MagicMock()
    c.request.side_effect = __import__("httpx").HTTPStatusError(
        "err", request=__import__("httpx").Request("GET", "http://x"),
        response=__import__("httpx").Response(404, text="nope"),
    )

    @forgejo_errors
    def f(client):
        return do_get_repo(client, "owner", "repo")

    with pytest.raises(RuntimeError, match="404"):
        f(c)
