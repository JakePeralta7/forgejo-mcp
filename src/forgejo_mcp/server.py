"""forgejo-mcp: an MCP server (stdio) for the Forgejo REST API.

Configuration comes exclusively from environment variables; a single httpx
client is created at startup. Domain helpers and tool registrations live in
``forgejo_mcp.helpers.*`` and are imported here for side effects (registering
tools on the shared ``mcp`` server).
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import wraps
from typing import Any

import httpx
from mcp.server import MCPServer

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}

READ_ONLY = {"readOnlyHint": True}

_DEFAULT_TIMEOUT = 30.0

_NAME = "forgejo-mcp"
_VERSION = "0.1.0"


@dataclass(frozen=True)
class Settings:
    url: str
    access_token: str
    user_agent: str
    timeout: float
    tls_insecure: bool


def env_bool(name: str, env: Mapping[str, str], default: bool) -> bool:
    raw = env.get(name)
    if raw is None or raw.strip() == "":
        return default
    value = raw.strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise RuntimeError(f"Invalid boolean for {name}: {raw!r} (use true/false/1/0)")


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env
    url = env.get("FORGEJO_URL", "").strip()
    access_token = env.get("FORGEJO_ACCESS_TOKEN", "").strip()
    if not url:
        raise RuntimeError("FORGEJO_URL is required")
    if not access_token:
        raise RuntimeError("FORGEJO_ACCESS_TOKEN is required")
    timeout_raw = env.get("FORGEJO_TIMEOUT", "").strip()
    try:
        timeout = float(timeout_raw) if timeout_raw else _DEFAULT_TIMEOUT
    except ValueError:
        raise RuntimeError(f"Invalid FORGEJO_TIMEOUT: {timeout_raw!r}") from None
    if timeout <= 0:
        raise RuntimeError(f"FORGEJO_TIMEOUT must be positive: {timeout!r}")
    return Settings(
        url=url.rstrip("/"),
        access_token=access_token,
        user_agent=env.get("FORGEJO_USER_AGENT", "").strip() or f"{_NAME}/{_VERSION}",
        timeout=timeout,
        tls_insecure=env_bool("FORGEJO_TLS_INSECURE", env, False),
    )


def create_client(settings: Settings) -> httpx.Client:
    return httpx.Client(
        base_url=f"{settings.url}/api/v1",
        headers={
            "Authorization": f"token {settings.access_token}",
            "User-Agent": settings.user_agent,
            "Accept": "application/json",
        },
        timeout=settings.timeout,
        verify=not settings.tls_insecure,
    )


_client: httpx.Client | None = None


def set_client(client: httpx.Client | None) -> None:
    global _client
    _client = client


def get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = create_client(load_settings())
    return _client


def forgejo_errors(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Convert httpx/network/validation errors into RuntimeError (MCP isError)."""

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            try:
                detail = exc.response.json()
                message = detail.get("message") if isinstance(detail, dict) else None
            except (ValueError, AttributeError):
                message = None
            text = message or exc.response.text.strip() or exc.__class__.__name__
            raise RuntimeError(f"HTTP {status}: {text}") from exc
        except (httpx.TransportError, httpx.HTTPError, OSError) as exc:
            raise RuntimeError(str(exc).strip() or exc.__class__.__name__) from exc
        except ValueError as exc:
            raise RuntimeError(str(exc).strip() or exc.__class__.__name__) from exc

    return wrapper


mcp = MCPServer(_NAME)


# Import domain modules for their `@mcp.tool` registration side effects.
# (Order matters only for readability; each module imports `mcp` and `get_client`
#  from this server module.)
from forgejo_mcp.helpers import actions, files, issues, orgs, pulls, repos, user  # noqa: E402,F401


def main() -> None:
    global _client
    settings = load_settings()
    _client = create_client(settings)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
