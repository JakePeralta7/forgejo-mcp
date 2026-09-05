from unittest.mock import MagicMock

import httpx

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


def patch_httpx(monkeypatch):
    fake = MagicMock()
    monkeypatch.setattr(server.httpx, "Client", fake)
    return fake


class TestCreateClient:
    def test_defaults(self, monkeypatch):
        fake = patch_httpx(monkeypatch)
        create_client(make_settings())
        kwargs = fake.call_args.kwargs
        assert kwargs["base_url"] == "https://codeberg.org/api/v1"
        assert kwargs["headers"]["Authorization"] == "token secret"
        assert kwargs["headers"]["User-Agent"] == "forgejo-mcp/0.1.0"
        assert kwargs["timeout"] == 30.0
        assert kwargs["verify"] is True

    def test_tls_insecure_disables_verify(self, monkeypatch):
        fake = patch_httpx(monkeypatch)
        create_client(make_settings(tls_insecure=True))
        assert fake.call_args.kwargs["verify"] is False

    def test_custom_user_agent(self, monkeypatch):
        fake = patch_httpx(monkeypatch)
        create_client(make_settings(user_agent="agent/1.0"))
        assert fake.call_args.kwargs["headers"]["User-Agent"] == "agent/1.0"


class FakeResponse:
    def __init__(self, payload=None, headers=None, status=200, text="", json_exc=None):
        self._payload = payload
        self.headers = headers or {}
        self.status_code = status
        self.text = text
        self._json_exc = json_exc

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "err", request=httpx.Request("GET", "http://x"), response=self
            )

    def json(self):
        if self._json_exc:
            raise self._json_exc
        return self._payload


def test_request_joins_api_v1_path():
    client = MagicMock()
    client.request.return_value = FakeResponse({}, status=200)
    request(client, "GET", "repos/a/b")
    path = client.request.call_args.args[1]
    assert path == "/repos/a/b"


def test_request_forwards_params_and_json():
    client = MagicMock()
    client.request.return_value = FakeResponse({}, status=200)
    request(client, "POST", "/repos/a/b/issues", params={"state": "open"}, json={"title": "x"})
    kwargs = client.request.call_args.kwargs
    assert kwargs["params"] == {"state": "open"}
    assert kwargs["json"] == {"title": "x"}


def test_request_raises_on_non_2xx():
    client = MagicMock()
    client.request.return_value = FakeResponse({}, status=404, text="Not Found")
    try:
        request(client, "GET", "/repos/a/b")
        raised = False
    except httpx.HTTPStatusError:
        raised = True
    assert raised


def test_list_page_envelope_with_total_count():
    client = MagicMock()
    client.request.return_value = FakeResponse(
        [{"id": 1}], headers={"x-total-count": "5"}, status=200
    )
    result = list_page(client, "GET", "/user/repos", params={"page": 1})
    assert result == {"items": [{"id": 1}], "total_count": 5}


def test_list_page_total_count_zero_when_absent():
    client = MagicMock()
    client.request.return_value = FakeResponse([], status=200)
    result = list_page(client, "GET", "/user/repos", params=None)
    assert result["total_count"] == 0


class TestPaginationParams:
    def test_empty(self):
        assert pagination_params() == {}

    def test_page(self):
        assert pagination_params(page=2) == {"page": 2}

    def test_limit_clamped(self):
        assert pagination_params(limit=500)["limit"] == 100

    def test_page_below_one_raises(self):
        try:
            pagination_params(page=0)
            raised = False
        except ValueError:
            raised = True
        assert raised
