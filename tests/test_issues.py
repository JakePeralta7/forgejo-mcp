from unittest.mock import MagicMock

import pytest

import forgejo_mcp.server as server
from forgejo_mcp.helpers.issues import (
    do_create_issue,
    do_create_issue_comment,
    do_delete_issue_comment,
    do_edit_issue_comment,
    do_get_issue,
    do_list_issue_comments,
    do_list_issues,
    do_update_issue,
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


class TestListIssues:
    def test_filters(self, client):
        json_response(client, [{"number": 1}], headers={"x-total-count": "1"})
        do_list_issues(client, "owner", "repo", state="open", labels="bug,enh")
        kwargs = client.request.call_args.kwargs
        assert kwargs["params"]["state"] == "open"
        assert kwargs["params"]["labels"] == "bug,enh"


class TestGetIssue:
    def test_path(self, client):
        json_response(client, {"number": 3})
        result = do_get_issue(client, "owner", "repo", 3)
        assert result["number"] == 3
        assert client.request.call_args.args[1] == "/repos/owner/repo/issues/3"


class TestCreateIssue:
    def test_body(self, client):
        json_response(client, {"number": 1}, status=201)
        do_create_issue(client, "owner", "repo", "Bug", body="desc", labels=["1"])
        kwargs = client.request.call_args.kwargs
        assert kwargs["json"] == {"title": "Bug", "body": "desc", "labels": [1]}
        assert client.request.call_args.args[0] == "POST"

    def test_labels_accept_ids(self, client):
        json_response(client, {"number": 1}, status=201)
        do_create_issue(client, "owner", "repo", "Bug", labels=[3, 4])
        kwargs = client.request.call_args.kwargs
        assert kwargs["json"] == {"title": "Bug", "labels": [3, 4]}


class TestUpdateIssue:
    def test_patch(self, client):
        json_response(client, {"number": 1})
        do_update_issue(client, "owner", "repo", 1, state="closed")
        args, kwargs = client.request.call_args
        assert args[0] == "PATCH"
        assert kwargs["json"] == {"state": "closed"}


class TestComments:
    def test_list(self, client):
        json_response(client, [{"id": 9}], headers={"x-total-count": "1"})
        result = do_list_issue_comments(client, "owner", "repo", 1)
        assert result["items"][0]["id"] == 9

    def test_create(self, client):
        json_response(client, {"id": 9}, status=201)
        do_create_issue_comment(client, "owner", "repo", 1, "hi")
        kwargs = client.request.call_args.kwargs
        assert kwargs["json"] == {"body": "hi"}

    def test_edit(self, client):
        json_response(client, {"id": 9})
        do_edit_issue_comment(client, "owner", "repo", 1, 9, "edited")
        args, kwargs = client.request.call_args
        assert args[0] == "PATCH"
        assert args[1] == "/repos/owner/repo/issues/comments/9"
        assert kwargs["json"] == {"body": "edited"}

    def test_delete(self, client):
        json_response(client, {}, status=204)
        result = do_delete_issue_comment(client, "owner", "repo", 1, 9)
        assert result["deleted"] is True
        assert client.request.call_args.args[0] == "DELETE"
        assert client.request.call_args.args[1] == "/repos/owner/repo/issues/comments/9"
