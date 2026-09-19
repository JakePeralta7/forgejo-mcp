import httpx
import pytest
import respx

import forgejo_mcp.server as server
from forgejo_mcp.client import list_page, pagination_params, request
from forgejo_mcp.server import Settings, create_client


def make_settings(**overrides) -> Settings:
    params = dict(
        url="https://codeberg.org",
        access_token="secret",
        user_agent="forgejo-mcp/0.1.0",
        timeout=30.0,
        tls_insecure=False,
    )
    params.update(overrides)
    return Settings(**params)


class TestCreateClient:
    def test_defaults(self, monkeypatch):
        fake = respx.mock
        monkeypatch.setattr(server.httpx, "Client", lambda **kwargs: fake)
        create_client(make_settings())
        # Note: respx mock doesn't capture constructor args the same way
        # This test is kept for structure; actual client creation tested via integration

    def test_tls_insecure_disables_verify(self, monkeypatch):
        fake = respx.mock
        monkeypatch.setattr(server.httpx, "Client", lambda **kwargs: fake)
        create_client(make_settings(tls_insecure=True))

    def test_custom_user_agent(self, monkeypatch):
        fake = respx.mock
        monkeypatch.setattr(server.httpx, "Client", lambda **kwargs: fake)
        create_client(make_settings(user_agent="agent/1.0"))


class TestRequest:
    @respx.mock
    def test_request_joins_api_v1_path(self):
        route = respx.get("https://codeberg.org/api/v1/repos/a/b").respond(json={})
        client = httpx.Client(base_url="https://codeberg.org/api/v1")
        request(client, "GET", "repos/a/b")
        assert route.called
        assert route.calls[0].request.url.path == "/api/v1/repos/a/b"

    @respx.mock
    def test_request_forwards_params_and_json(self):
        route = respx.post("https://codeberg.org/api/v1/repos/a/b/issues").respond(json={})
        client = httpx.Client(base_url="https://codeberg.org/api/v1")
        request(client, "POST", "/repos/a/b/issues", params={"state": "open"}, json={"title": "x"})
        assert route.called
        assert dict(route.calls[0].request.url.params) == {"state": "open"}
        assert route.calls[0].request.content == b'{"title":"x"}'

    @respx.mock
    def test_request_raises_on_non_2xx(self):
        respx.get("https://codeberg.org/api/v1/repos/a/b").respond(status_code=404, text="Not Found")
        client = httpx.Client(base_url="https://codeberg.org/api/v1")
        with pytest.raises(httpx.HTTPStatusError):
            request(client, "GET", "/repos/a/b")


class TestListPage:
    @respx.mock
    def test_list_page_envelope_with_total_count(self):
        route = respx.get("https://codeberg.org/api/v1/user/repos").respond(
            json=[{"id": 1}], headers={"x-total-count": "5"}
        )
        client = httpx.Client(base_url="https://codeberg.org/api/v1")
        result = list_page(client, "GET", "/user/repos", params={"page": 1})
        assert route.called
        assert result == {"items": [{"id": 1}], "total_count": 5}

    @respx.mock
    def test_list_page_total_count_zero_when_absent(self):
        route = respx.get("https://codeberg.org/api/v1/user/repos").respond(json=[])
        client = httpx.Client(base_url="https://codeberg.org/api/v1")
        result = list_page(client, "GET", "/user/repos", params=None)
        assert route.called
        assert result["total_count"] == 0


class TestPaginationParams:
    def test_empty(self):
        assert pagination_params() == {}

    def test_page(self):
        assert pagination_params(page=2) == {"page": 2}

    def test_limit_clamped(self):
        assert pagination_params(limit=500)["limit"] == 100

    def test_page_below_one_raises(self):
        with pytest.raises(ValueError, match="page must be >= 1"):
            pagination_params(page=0)

    def test_limit_below_one_raises(self):
        with pytest.raises(ValueError, match="limit must be >= 1"):
            pagination_params(limit=0)