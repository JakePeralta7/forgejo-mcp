from unittest.mock import MagicMock

import pytest

import forgejo_mcp.server as server
from forgejo_mcp.helpers.orgs import (
    do_list_org_members,
    do_list_org_repos,
    do_list_user_orgs,
    do_search_org_teams,
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


class TestListUserOrgs:
    def test_path(self, client):
        json_response(client, [{"name": "org"}], headers={"x-total-count": "1"})
        result = do_list_user_orgs(client, "alice")
        assert result["items"][0]["name"] == "org"
        assert client.request.call_args.args[1] == "/users/alice/orgs"


class TestOrgRepos:
    def test_path(self, client):
        json_response(client, [{"name": "r"}], headers={"x-total-count": "1"})
        do_list_org_repos(client, "org", page=1, limit=20)
        kwargs = client.request.call_args.kwargs
        assert kwargs["params"] == {"page": 1, "limit": 20}
        assert client.request.call_args.args[1] == "/orgs/org/repos"


class TestOrgMembers:
    def test_path(self, client):
        json_response(client, [{"login": "u"}], headers={"x-total-count": "1"})
        result = do_list_org_members(client, "org")
        assert result["items"][0]["login"] == "u"
        assert client.request.call_args.args[1] == "/orgs/org/members"


class TestSearchOrgTeams:
    def test_search(self, client):
        json_response(client, [{"name": "team"}], headers={"x-total-count": "1"})
        do_search_org_teams(client, "org", q="dev")
        kwargs = client.request.call_args.kwargs
        assert kwargs["params"]["q"] == "dev"
        assert client.request.call_args.args[1] == "/orgs/org/teams/search"
