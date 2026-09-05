from unittest.mock import MagicMock

import pytest

import forgejo_mcp.server as server
from forgejo_mcp.helpers.pulls import (
    do_create_pull_review,
    do_create_pull_request,
    do_get_pull_review,
    do_get_pull_request,
    do_list_pull_review_comments,
    do_list_pull_reviews,
    do_list_pull_requests,
    do_merge_pull_request,
    do_update_pull_request,
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


class TestListPullRequests:
    def test_state_param(self, client):
        json_response(client, [{"number": 1}], headers={"x-total-count": "1"})
        do_list_pull_requests(client, "owner", "repo", state="open")
        kwargs = client.request.call_args.kwargs
        assert kwargs["params"]["state"] == "open"
        assert client.request.call_args.args[1] == "/repos/owner/repo/pulls"


class TestGetPullRequest:
    def test_path(self, client):
        json_response(client, {"number": 2})
        result = do_get_pull_request(client, "owner", "repo", 2)
        assert result["number"] == 2
        assert client.request.call_args.args[1] == "/repos/owner/repo/pulls/2"


class TestCreatePullRequest:
    def test_body(self, client):
        json_response(client, {"number": 1}, status=201)
        do_create_pull_request(client, "owner", "repo", "T", "feat", "main", body="d")
        kwargs = client.request.call_args.kwargs
        assert kwargs["json"] == {"title": "T", "head": "feat", "base": "main", "body": "d"}


class TestUpdatePullRequest:
    def test_patch(self, client):
        json_response(client, {"number": 1})
        do_update_pull_request(client, "owner", "repo", 1, title="New")
        args, kwargs = client.request.call_args
        assert args[0] == "PATCH"
        assert kwargs["json"] == {"title": "New"}


class TestMergePullRequest:
    def test_merge(self, client):
        resp = json_response(client, {}, status=200)
        resp.json.side_effect = Exception("json should not be called")
        result = do_merge_pull_request(client, "owner", "repo", 1, method="squash")
        args, kwargs = client.request.call_args
        assert args[0] == "POST"
        assert args[1] == "/repos/owner/repo/pulls/1/merge"
        assert kwargs["json"]["Do"] == "squash"
        assert result["merged"] is True
        assert result["status"] == 200


class TestReviews:
    def test_list(self, client):
        json_response(client, [{"id": 5}], headers={"x-total-count": "1"})
        result = do_list_pull_reviews(client, "owner", "repo", 1)
        assert result["items"][0]["id"] == 5

    def test_get(self, client):
        json_response(client, {"id": 5})
        result = do_get_pull_review(client, "owner", "repo", 1, 5)
        assert result["id"] == 5
        assert client.request.call_args.args[1] == "/repos/owner/repo/pulls/1/reviews/5"

    def test_list_comments(self, client):
        json_response(client, [{"id": 8}], headers={"x-total-count": "1"})
        result = do_list_pull_review_comments(client, "owner", "repo", 1, 5)
        assert result["items"][0]["id"] == 8
        assert client.request.call_args.args[1] == "/repos/owner/repo/pulls/1/reviews/5/comments"

    def test_create(self, client):
        json_response(client, {"id": 5}, status=201)
        do_create_pull_review(client, "owner", "repo", 1, "APPROVED", body="LGTM")
        kwargs = client.request.call_args.kwargs
        assert kwargs["json"] == {"event": "APPROVED", "body": "LGTM"}
