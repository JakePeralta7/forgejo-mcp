from unittest.mock import MagicMock

import pytest

import forgejo_mcp.server as server
from forgejo_mcp.helpers.user import (
    do_get_my_user,
    do_get_notifications,
    do_get_user,
    do_list_my_repos,
    do_mark_notifications_read,
    do_search_users,
)


@pytest.fixture
def client():
    c = MagicMock()
    server.set_client(c)
    yield c
    server.set_client(None)


def json_response(client, payload, headers=None):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.headers = headers or {}
    client.request.return_value = resp
    return resp


class TestGetUser:
    def test_path(self, client):
        json_response(client, {"id": 1, "login": "alice"})
        result = do_get_user(client, "alice")
        assert result["login"] == "alice"
        args, kwargs = client.request.call_args
        assert args[0] == "GET"
        assert args[1] == "/users/alice"


class TestSearchUsers:
    def test_shape_and_params(self, client):
        json_response(client, [{"id": 1}], headers={"x-total-count": "1"})
        result = do_search_users(client, "alice", limit=5)
        assert result == {"items": [{"id": 1}], "total_count": 1}
        kwargs = client.request.call_args.kwargs
        assert kwargs["params"]["q"] == "alice"
        assert kwargs["params"]["limit"] == 5


class TestGetMyUser:
    def test_path(self, client):
        json_response(client, {"id": 1, "login": "me"})
        result = do_get_my_user(client)
        assert result["login"] == "me"
        assert client.request.call_args.args[1] == "/user"


class TestListMyRepos:
    def test_paginated_envelope(self, client):
        json_response(client, [{"name": "r"}], headers={"x-total-count": "3"})
        result = do_list_my_repos(client, page=2, limit=50)
        assert result["total_count"] == 3
        kwargs = client.request.call_args.kwargs
        assert kwargs["params"] == {"page": 2, "limit": 50}


class TestNotifications:
    def test_get(self, client):
        json_response(client, [{"id": 7}], headers={"x-total-count": "1"})
        result = do_get_notifications(client)
        assert result["items"] == [{"id": 7}]

    def test_mark_read(self, client):
        json_response(client, [{"id": 1}])
        result = do_mark_notifications_read(client)
        assert result["marked_read"] is True
        args, kwargs = client.request.call_args
        assert args[0] == "PUT"
        assert args[1] == "/notifications"
        assert kwargs["params"] == {"all": "true"}
