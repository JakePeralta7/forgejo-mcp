"""forgejo-mcp: an MCP server (stdio) for the Forgejo REST API.

Configuration comes exclusively from environment variables; a single httpx
client is created at startup. Domain helpers and tool registrations live in
``forgejo_mcp.helpers.*`` and are imported here for side effects (registering
tools on the shared ``mcp`` server).
"""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import Callable, Mapping
from contextvars import ContextVar
from dataclasses import dataclass
from functools import wraps
from typing import Any

import httpx
from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from forgejo_mcp.client import create_transport

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}

READ_ONLY = ToolAnnotations(read_only_hint=True)

_DEFAULT_TIMEOUT = 30.0

_NAME = "forgejo-mcp"
_VERSION = "0.1.1"

# Correlation ID for request tracing
correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)

# Module logger
logger = logging.getLogger(__name__)

# Global read-only mode flag (set in main() after loading settings)
READ_ONLY_MODE = False


@dataclass(frozen=True)
class Settings:
    url: str
    access_token: str
    user_agent: str
    timeout: float
    tls_insecure: bool
    read_only: bool = False


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
        read_only=env_bool("FORGEJO_READ_ONLY", env, False),
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
        transport=create_transport(),
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


def new_correlation_id() -> str:
    """Generate a new correlation ID for request tracing."""
    return uuid.uuid4().hex[:12]


def set_correlation_id(cid: str | None = None) -> str:
    """Set and return a correlation ID (generates new if not provided)."""
    cid = cid or new_correlation_id()
    correlation_id.set(cid)
    return cid


def get_correlation_id() -> str | None:
    """Get the current correlation ID."""
    return correlation_id.get()


def forgejo_errors(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Convert httpx/network/validation errors into RuntimeError (MCP isError)."""

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        cid = set_correlation_id()
        logger.debug("tool_call_start", extra={"correlation_id": cid, "tool": fn.__name__, "args": _safe_args(args, kwargs)})
        try:
            result = fn(*args, **kwargs)
            logger.debug("tool_call_end", extra={"correlation_id": cid, "tool": fn.__name__, "success": True})
            return result
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            try:
                detail = exc.response.json()
                message = detail.get("message") if isinstance(detail, dict) else None
            except (ValueError, AttributeError):
                message = None
            text = message or exc.response.text.strip() or exc.__class__.__name__
            logger.error("tool_call_error", extra={"correlation_id": cid, "tool": fn.__name__, "error": f"HTTP {status}: {text}"})
            raise RuntimeError(f"HTTP {status}: {text}") from exc
        except (httpx.TransportError, httpx.HTTPError, OSError) as exc:
            logger.error("tool_call_error", extra={"correlation_id": cid, "tool": fn.__name__, "error": str(exc)})
            raise RuntimeError(str(exc).strip() or exc.__class__.__name__) from exc
        except ValueError as exc:
            logger.error("tool_call_error", extra={"correlation_id": cid, "tool": fn.__name__, "error": str(exc)})
            raise RuntimeError(str(exc).strip() or exc.__class__.__name__) from exc

    return wrapper


def _safe_args(args: tuple, kwargs: dict) -> dict:
    """Return a safe representation of args for logging (redact sensitive data)."""
    safe = {}
    for i, arg in enumerate(args):
        if isinstance(arg, str) and ("token" in arg.lower() or "secret" in arg.lower() or "password" in arg.lower()):
            safe[f"arg_{i}"] = "[REDACTED]"
        else:
            safe[f"arg_{i}"] = str(arg)[:200]
    for k, v in kwargs.items():
        if "token" in k.lower() or "secret" in k.lower() or "password" in k.lower():
            safe[k] = "[REDACTED]"
        else:
            safe[k] = str(v)[:200]
    return safe


mcp = MCPServer(_NAME)


# Import domain modules for their `@mcp.tool` registration side effects.
# (Order matters only for readability; each module imports `mcp` and `get_client`
#  from this server module.)
from forgejo_mcp.helpers import actions, files, issues, orgs, pulls, repos, user  # noqa: E402,F401


def main() -> None:
    global _client, READ_ONLY_MODE
    settings = load_settings()
    READ_ONLY_MODE = settings.read_only
    
    # Configure logging to stderr (never stdout for stdio transport)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s [%(correlation_id)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )
    
    logger.info("server_start", extra={"correlation_id": "init", "read_only": READ_ONLY_MODE, "version": _VERSION})
    
    _client = create_client(settings)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
