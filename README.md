# forgejo-mcp

An MCP server (stdio) for the [Forgejo](https://forgejo.org) REST API. Connect
your AI assistant to any Forgejo instance (e.g. Codeberg) to manage
repositories, issues, pull requests, files, commits, Actions workflow runs,
organizations, and notifications through natural language.

Single Python package, one HTTP client created at startup, configuration via
environment variables only. Built on the official
[`mcp`](https://pypi.org/project/mcp/) SDK (high-level server API) and `httpx`.

## Configuration (environment variables)

| Variable                  | Required | Default                | Description                                                        |
| ------------------------- | -------- | ---------------------- | ------------------------------------------------------------------ |
| `FORGEJO_URL`             | yes      | —                      | Forgejo instance base URL, e.g. `https://codeberg.org`             |
| `FORGEJO_ACCESS_TOKEN`    | yes      | —                      | Personal access token                                              |
| `FORGEJO_USER_AGENT`      | no       | `forgejo-mcp/<version>`| HTTP `User-Agent` header                                           |
| `FORGEJO_TIMEOUT`         | no       | `30`                   | HTTP request timeout, seconds                                      |
| `FORGEJO_TLS_INSECURE`    | no       | `false`                | `true` disables TLS certificate verification (self-signed)         |

Missing `FORGEJO_URL`/`FORGEJO_ACCESS_TOKEN` or an invalid boolean abort
startup with a clear error. Booleans accept `true/false/1/0/yes/no`
(case-insensitive).

Create a token at *Settings → Applications → Access Tokens* with the scopes
your operations need (e.g. `read:repository`, `write:issue`,
`write:repository`).

## Tools

All requests are scoped to `{FORGEJO_URL}/api/v1`. Pageable list tools accept
`page`/`limit` and return `{items, total_count}` (`total_count` is read from
the `x-total-count` response header).

### User & notifications
| Tool | Description | Read-only |
| --- | --- | --- |
| `get_user(username)` | Get info about a user | yes |
| `search_users(q, limit=10)` | Search for users | yes |
| `list_my_repos(page, limit)` | List repositories owned by the authenticated user | yes |
| `get_notifications(page, limit)` | List user notifications | yes |
| `mark_notifications_read()` | Mark all notifications read | no |

### Repositories
| Tool | Description | Read-only |
| --- | --- | --- |
| `get_repo(owner, repo)` | Get a repository | yes |
| `list_repos(owner, page, limit)` | List an owner's repositories | yes |
| `search_repos(q, page, limit)` | Search repositories | yes |
| `create_repo(name, private, description)` | Create a repository | no |
| `fork_repo(owner, repo)` | Fork a repository | no |
| `delete_repo(owner, repo)` | Delete a repository | no |
| `list_branches(owner, repo, page, limit)` | List branches | yes |
| `create_branch(owner, repo, new_branch, old_ref)` | Create a branch | no |
| `delete_branch(owner, repo, branch)` | Delete a branch | no |
| `list_labels(owner, repo, page, limit)` | List issue labels | yes |
| `create_label(owner, repo, name, color)` | Create a label | no |
| `list_milestones(owner, repo, state, page, limit)` | List milestones | yes |
| `create_milestone(owner, repo, title, description)` | Create a milestone | no |
| `list_repo_topics(owner, repo)` | List a repo's topics | yes |

### Files & commits
| Tool | Description | Read-only |
| --- | --- | --- |
| `get_file_content(owner, repo, filepath, ref)` | Read a file (UTF-8 text or `{encoding:base64,...}`) | yes |
| `list_repo_commits(owner, repo, branch, page, limit)` | List commits | yes |
| `get_commit(owner, repo, sha)` | Get a single commit | yes |
| `create_file(owner, repo, filepath, content, message, branch, base64)` | Create a file | no |
| `update_file(owner, repo, filepath, content, message, branch, sha, base64)` | Update a file | no |
| `delete_file(owner, repo, filepath, message, branch, sha)` | Delete a file | no |

### Issues
| Tool | Description | Read-only |
| --- | --- | --- |
| `list_issues(owner, repo, state, labels, page, limit)` | List issues | yes |
| `get_issue(owner, repo, index)` | Get an issue | yes |
| `create_issue(owner, repo, title, body, labels)` | Create an issue (`labels` = numeric label IDs) | no |
| `update_issue(owner, repo, index, title, body, state)` | Update an issue | no |
| `list_issue_comments(owner, repo, index, page, limit)` | List issue/PR comments | yes |
| `create_issue_comment(owner, repo, index, body)` | Add a comment | no |
| `edit_issue_comment(owner, repo, index, comment_id, body)` | Edit a comment | no |
| `delete_issue_comment(owner, repo, index, comment_id)` | Delete a comment | no |

### Pull requests & reviews
| Tool | Description | Read-only |
| --- | --- | --- |
| `list_pull_requests(owner, repo, state, page, limit)` | List pull requests | yes |
| `get_pull_request(owner, repo, index)` | Get a pull request | yes |
| `create_pull_request(owner, repo, title, head, base, body)` | Create a pull request | no |
| `update_pull_request(owner, repo, index, title, body, state)` | Update a pull request | no |
| `merge_pull_request(owner, repo, index, method)` | Merge a pull request | no |
| `list_pull_reviews(owner, repo, index)` | List PR reviews | yes |
| `get_pull_review(owner, repo, index, review_id)` | Get a PR review | yes |
| `list_pull_review_comments(owner, repo, index, review_id)` | List comments on a PR review | yes |
| `create_pull_review(owner, repo, index, event, body)` | Submit a PR review | no |

### CI/CD Actions
| Tool | Description | Read-only |
| --- | --- | --- |
| `list_workflow_runs(owner, repo, status, event, page, limit)` | List workflow runs | yes |
| `get_workflow_run(owner, repo, run_id)` | Get a workflow run | yes |
| `dispatch_workflow(owner, repo, workflow_id, ref)` | Trigger `workflow_dispatch` | no |

### Organizations
| Tool | Description | Read-only |
| --- | --- | --- |
| `list_user_orgs(username)` | List a user's organizations | yes |
| `list_org_repos(org, page, limit)` | List an org's repositories | yes |
| `list_org_members(org, page, limit)` | List an org's members | yes |
| `search_org_teams(org, q, page, limit)` | Search teams in an org | yes |

Tool errors are raised as short `RuntimeError` messages and surfaced by MCP as
error results.

## Example configuration

```json
{
  "mcpServers": {
    "forgejo": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/YOURNAME/forgejo-mcp", "forgejo-mcp"],
      "env": {
        "FORGEJO_URL": "https://codeberg.org",
        "FORGEJO_ACCESS_TOKEN": "<your personal access token>"
      }
    }
  }
}
```

With Docker, pass secrets through from your environment so they never appear
in the config file:

```json
{
  "mcpServers": {
    "forgejo": {
      "command": "docker",
      "args": ["run", "-i", "--rm",
        "-e", "FORGEJO_URL",
        "-e", "FORGEJO_ACCESS_TOKEN",
        "ghcr.io/YOURNAME/forgejo-mcp:latest"]
    }
  }
}
```

`-e VAR` without a value passes the variable through from your shell.

## Development

```bash
uv sync --group dev   # install deps into .venv
uv run pytest -q      # unit tests (httpx mocked, no network)
docker build -t forgejo-mcp:dev .
```

Entrypoint: `python -m forgejo_mcp` (stdio transport only).

## Releasing

Every push to `main` runs tests, then publishes
`ghcr.io/<owner>/<repo>:<version>` + `:latest`, where `<version>` is read from
`version` in `pyproject.toml`. To release, bump the version and merge to main.
Git tags are not used.

## License

[MIT](LICENSE)
