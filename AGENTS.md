# AGENTS.md

## Commands

- Install deps: `uv sync --group dev` (creates `.venv`; Python >= 3.12)
- Tests: `uv run pytest -q` — single test: `uv run pytest tests/test_issues.py -k name`
- Build image: `docker build -t forgejo-mcp:dev .`
- Run server: `uv run python -m forgejo_mcp` (fails fast with `RuntimeError`
  unless `FORGEJO_URL`/`FORGEJO_ACCESS_TOKEN` are set)
- There is no lint/typecheck config; pytest is the only automated gate.
- Committed `pyrightconfig.json` points Pyright at `.venv`: until `uv sync`
  has run, editors show false "Import could not be resolved" errors for
  mcp/httpx/pytest — install deps before trusting diagnostics.
- Dev shell is Windows PowerShell: inline `python -c "..."` breaks on quoting —
  write a temp `.py` file instead.

## Layout / architecture

This project intentionally mirrors the structure and conventions of
`s3-mcp` (a single, small server entry plus testable plain helpers). Unlike
s3-mcp, which keeps ~11 tools in one module, forgejo-mcp exposes ~40 tools, so
the helpers/tools are split by domain while keeping one thin entry module.

- `src/forgejo_mcp/server.py`: env parsing (`load_settings`) -> HTTP client
  factory (`create_client`) -> `@forgejo_errors` decorator -> the
  `MCPServer` instance where every domain's tools are registered -> `main()`.
- `src/forgejo_mcp/client.py`: the only place that talks HTTP. Provides a
  paginated, response-envelope-aware `request(client, method, path, ...)`
  helper shared by all domain modules.
- `src/forgejo_mcp/helpers/` — one module per domain (`user`, `repos`,
  `files`, `issues`, `pulls`, `actions`, `orgs`). Each defines plain
  synchronous `do_*(client, ...)` helpers that take the httpx client as the
  first argument, plus the `@tool` registrations on the shared `mcp` server.
  New tools must follow this split; tests call helpers directly with a
  MagicMock httpx client and never go through async MCP machinery.
- Entrypoint chain: `python -m forgejo_mcp` -> `__main__.py` ->
  `server.main()` builds ONE httpx client from env, registers all domain
  tools, then `mcp.run(transport="stdio")`.
- The client lives in a module global (`_client`) set by `main()` or injected
  in tests via `server.set_client(client)`. Never build clients at import time.
- A dict return from a tool reaches test clients as
  `structured_content == {"result": ...}`.

## Config / env conventions

- `load_settings(env)` returns a frozen `Settings` dataclass. Required:
  `FORGEJO_URL`, `FORGEJO_ACCESS_TOKEN`. Optional: `FORGEJO_USER_AGENT`,
  `FORGEJO_TIMEOUT`, `FORGEJO_TLS_INSECURE`. Missing required vars abort
  startup.
- Booleans (`FORGEJO_TLS_INSECURE`) accept `true/false/1/0/yes/no`
  (case-insensitive); invalid values raise `RuntimeError`.
- The client sends `Authorization: token <token>` (Forgejo's convention).

## mcp SDK v2 pitfalls (`mcp>=2,<3`)

- Import is `from mcp.server import MCPServer`. `mcp.server.fastmcp.FastMCP`
  was removed in v2 — old tutorials/snippets will not import.
- Pydantic fields are snake_case (`is_error`, `structured_content`,
  `server_info`); the JSON wire stays camelCase via aliases.
- Plain dicts are accepted for `@mcp.tool(annotations={...})`;
  `ToolAnnotations` from `mcp_types` also works.
- Errors: helpers that can fail are wrapped in `@forgejo_errors`, which
  converts httpx HTTP/transport errors and `ValueError` into a short
  `RuntimeError` (MCP turns that into an isError result). Raise `ValueError`
  inside helpers for validation failures (e.g. bad page/limit).
- `@tool` handlers must remain synchronous. Helpers that do network I/O are
  synchronous httpx calls.

## API / pagination conventions (Forgejo REST)

- Base path is `{FORGEJO_URL}/api/v1`. Requests go through
  `client.request()` which joins the path and raises on non-2xx.
- Fetching a JSON dict/body should be driven by `expected` so the shared
  helper can validate/serialize. New endpoints should route through
  `client.request` rather than reaching into httpx directly.
- Pageable list helpers return `{"items": [...], "total_count": n}`.
  `total_count` comes from the `x-total-count` response header (0 when
  absent). Pass `page`/`limit` as query params; clamp `limit` to a sane max.
- File content: `get_file_content` returns UTF-8 `text` or a
  `{encoding: "base64", ...}` envelope for binary content; `create_file` /
  `update_file` accept a `base64` flag to decode base64 content to bytes.

## Testing rules

- Unit tests must not touch the network — mock the httpx client with
  `MagicMock`. Fixtures live in the test files (no conftest.py); tests use
  `server.set_client`.
- Each `test_<domain>.py` file asserts request path/params and result shaping
  for that domain's helpers, plus error-wrapping cases (HTTP error ->
  RuntimeError) and pagination envelopes.
- Live checks against a real endpoint are manual only: spawn the server
  via `mcp.client.stdio.StdioServerParameters` with `FORGEJO_URL` and
  `FORGEJO_ACCESS_TOKEN` set. Never hardcode credentials; pass them through env.

## Packaging / release gotchas

- `README.md` is referenced by hatchling AND copied in the Dockerfile builder
  stage — renaming/removing it breaks both builds.
- `uv.lock` is committed; re-run `uv sync` after touching dependencies so it
  updates.
- `.github/workflows/release.yml`: every push to main runs pytest, then builds
  and pushes `ghcr.io/<lowercased repo>:<pyproject version>` plus `:latest`.
  Releasing = bump `version` in pyproject.toml and push to main. Git tags are
  NOT used for releases and trigger nothing.
