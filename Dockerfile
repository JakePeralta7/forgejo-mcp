# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# Dependencies layer (cached independently of app source).
COPY pyproject.toml README.md ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --target=/install "mcp>=2,<3" "httpx>=0.27"

# App layer.
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-deps --target=/install .


FROM python:3.12-slim
LABEL org.opencontainers.image.title="forgejo-mcp" \
      org.opencontainers.image.description="MCP server (stdio) for the Forgejo REST API." \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/JakePeralta7/forgejo-mcp"
RUN groupadd --system app && useradd --system --gid app --home-dir /nonexistent app
COPY --from=builder /install/ /usr/local/lib/python3.12/site-packages/
ENV PYTHONUNBUFFERED=1
USER app
ENTRYPOINT ["python", "-m", "forgejo_mcp"]
