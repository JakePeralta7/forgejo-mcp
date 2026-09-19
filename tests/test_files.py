import base64

from unittest.mock import MagicMock

import pytest

import forgejo_mcp.server as server
from forgejo_mcp.helpers.files import (
    do_create_file,
    do_delete_file,
    do_get_commit,
    do_get_file_content,
    do_list_repo_commits,
    do_list_repo_files,
    do_update_file,
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


class TestGetFileContent:
    def test_utf8_text(self, client):
        raw = "héllo".encode("utf-8")
        json_response(client, {"content": base64.b64encode(raw).decode(), "encoding": "base64", "sha": "abc"})
        result = do_get_file_content(client, "owner", "repo", "README.md", ref="main")
        assert result["encoding"] == "utf-8"
        assert result["text"] == "héllo"
        assert result["sha"] == "abc"
        assert client.request.call_args.args[1] == "/repos/owner/repo/contents/README.md"
        assert client.request.call_args.kwargs["params"] == {"ref": "main"}

    def test_binary_base64(self, client):
        raw = bytes(range(256))
        json_response(client, {"content": base64.b64encode(raw).decode(), "encoding": "base64", "sha": "abc"})
        result = do_get_file_content(client, "owner", "repo", "blob.bin")
        assert result["encoding"] == "base64"
        assert base64.b64decode(result["base64"]) == raw
        assert "text" not in result

    def test_no_ref_no_query(self, client):
        json_response(client, {"content": base64.b64encode(b"x").decode(), "encoding": "base64"})
        do_get_file_content(client, "owner", "repo", "f.txt")
        assert client.request.call_args.args[1] == "/repos/owner/repo/contents/f.txt"
        assert client.request.call_args.kwargs["params"] is None


class TestListRepoCommits:
    def test_with_branch(self, client):
        json_response(client, [{"sha": "a"}], headers={"x-total-count": "1"})
        do_list_repo_commits(client, "owner", "repo", branch="main", limit=30)
        kwargs = client.request.call_args.kwargs
        assert kwargs["params"]["sha"] == "main"

    def test_no_branch_no_sha(self, client):
        json_response(client, [{"sha": "a"}], headers={"x-total-count": "1"})
        do_list_repo_commits(client, "owner", "repo")
        kwargs = client.request.call_args.kwargs
        assert "sha" not in kwargs["params"]


class TestGetCommit:
    def test_path(self, client):
        json_response(client, {"sha": "abc"})
        result = do_get_commit(client, "owner", "repo", "abc")
        assert result["sha"] == "abc"
        assert client.request.call_args.args[1] == "/repos/owner/repo/git/commits/abc"


class TestCreateFile:
    def test_text_encoded_base64(self, client):
        json_response(client, {"content": {}}, status=201)
        do_create_file(client, "owner", "repo", "a.txt", "hello", "msg", branch="main")
        kwargs = client.request.call_args.kwargs
        assert kwargs["json"]["content"] == base64.b64encode(b"hello").decode()
        assert kwargs["json"]["branch"] == "main"
        assert client.request.call_args.args[1] == "/repos/owner/repo/contents/a.txt"

    def test_base64_flag_passes_through(self, client):
        json_response(client, {"content": {}}, status=201)
        raw = b"\x00\x01\xff"
        do_create_file(client, "owner", "repo", "a.bin", base64.b64encode(raw).decode(), "msg", base64=True)
        kwargs = client.request.call_args.kwargs
        assert kwargs["json"]["content"] == base64.b64encode(raw).decode()


class TestUpdateFile:
    def test_with_sha(self, client):
        json_response(client, {"content": {}}, status=200)
        do_update_file(client, "owner", "repo", "a.txt", "v2", "msg", branch="main", sha="abc")
        kwargs = client.request.call_args.kwargs
        assert kwargs["json"]["sha"] == "abc"
        assert client.request.call_args.args[0] == "PUT"


class TestDeleteFile:
    def test_delete(self, client):
        json_response(client, {}, status=200)
        do_delete_file(client, "owner", "repo", "a.txt", "msg", branch="main", sha="abc")
        args, kwargs = client.request.call_args
        assert args[0] == "DELETE"
        assert args[1] == "/repos/owner/repo/contents/a.txt"
        assert kwargs["json"]["sha"] == "abc"


def _resp(payload, headers=None, status=200):
    r = MagicMock()
    r.json.return_value = payload
    r.headers = headers or {}
    r.status_code = status
    return r


class TestListRepoFiles:
    def test_root_default_branch(self, client):
        client.request.side_effect = [
            _resp({"default_branch": "main"}),
            _resp({
                "tree": [
                    {"path": "README.md", "type": "blob", "sha": "sha1", "size": 100, "mode": "100644"},
                    {"path": "src/main.py", "type": "blob", "sha": "sha2", "size": 200, "mode": "100644"},
                    {"path": "src/utils.py", "type": "blob", "sha": "sha3", "size": 150, "mode": "100644"},
                    {"path": "tests/test.py", "type": "blob", "sha": "sha4", "size": 300, "mode": "100644"},
                ]
            }),
        ]
        result = do_list_repo_files(client, "owner", "repo")
        assert result["total_count"] == 4
        assert len(result["items"]) == 4
        assert result["items"][0]["path"] == "README.md"
        assert result["items"][0]["type"] == "blob"
        assert client.request.call_args_list[0].args[1] == "/repos/owner/repo"
        assert client.request.call_args_list[1].args[1] == "/repos/owner/repo/git/trees/main"
        assert client.request.call_args_list[1].kwargs["params"] == {"recursive": "1", "per_page": 1000}

    def test_with_ref(self, client):
        client.request.side_effect = [
            _resp({
                "tree": [
                    {"path": "README.md", "type": "blob", "sha": "sha1", "size": 100, "mode": "100644"},
                ]
            }),
        ]
        result = do_list_repo_files(client, "owner", "repo", ref="v1.0.0")
        assert result["total_count"] == 1
        assert client.request.call_args.args[1] == "/repos/owner/repo/git/trees/v1.0.0"

    def test_path_filter(self, client):
        client.request.side_effect = [
            _resp({"default_branch": "main"}),
            _resp({
                "tree": [
                    {"path": "README.md", "type": "blob", "sha": "sha1", "size": 100, "mode": "100644"},
                    {"path": "src/main.py", "type": "blob", "sha": "sha2", "size": 200, "mode": "100644"},
                    {"path": "src/utils.py", "type": "blob", "sha": "sha3", "size": 150, "mode": "100644"},
                    {"path": "tests/test.py", "type": "blob", "sha": "sha4", "size": 300, "mode": "100644"},
                ]
            }),
        ]
        result = do_list_repo_files(client, "owner", "repo", path="/src/")
        assert result["total_count"] == 2
        assert result["items"][0]["path"] == "src/main.py"
        assert result["items"][1]["path"] == "src/utils.py"

    def test_path_without_trailing_slash(self, client):
        client.request.side_effect = [
            _resp({"default_branch": "main"}),
            _resp({
                "tree": [
                    {"path": "src/main.py", "type": "blob", "sha": "sha2", "size": 200, "mode": "100644"},
                    {"path": "src/utils.py", "type": "blob", "sha": "sha3", "size": 150, "mode": "100644"},
                ]
            }),
        ]
        result = do_list_repo_files(client, "owner", "repo", path="/src")
        assert result["total_count"] == 2

    def test_depth_zero(self, client):
        client.request.side_effect = [
            _resp({"default_branch": "main"}),
            _resp({
                "tree": [
                    {"path": "README.md", "type": "blob", "sha": "sha1", "size": 100, "mode": "100644"},
                    {"path": "src/main.py", "type": "blob", "sha": "sha2", "size": 200, "mode": "100644"},
                    {"path": "src/utils.py", "type": "blob", "sha": "sha3", "size": 150, "mode": "100644"},
                    {"path": "src/sub/deep.py", "type": "blob", "sha": "sha4", "size": 300, "mode": "100644"},
                ]
            }),
        ]
        result = do_list_repo_files(client, "owner", "repo", depth=0)
        assert result["total_count"] == 1
        assert result["items"][0]["path"] == "README.md"

    def test_depth_one(self, client):
        client.request.side_effect = [
            _resp({"default_branch": "main"}),
            _resp({
                "tree": [
                    {"path": "README.md", "type": "blob", "sha": "sha1", "size": 100, "mode": "100644"},
                    {"path": "src/main.py", "type": "blob", "sha": "sha2", "size": 200, "mode": "100644"},
                    {"path": "src/utils.py", "type": "blob", "sha": "sha3", "size": 150, "mode": "100644"},
                    {"path": "src/sub/deep.py", "type": "blob", "sha": "sha4", "size": 300, "mode": "100644"},
                ]
            }),
        ]
        result = do_list_repo_files(client, "owner", "repo", depth=1)
        assert result["total_count"] == 3
        paths = {item["path"] for item in result["items"]}
        assert paths == {"README.md", "src/main.py", "src/utils.py"}

    def test_depth_with_path(self, client):
        client.request.side_effect = [
            _resp({"default_branch": "main"}),
            _resp({
                "tree": [
                    {"path": "src/main.py", "type": "blob", "sha": "sha2", "size": 200, "mode": "100644"},
                    {"path": "src/utils.py", "type": "blob", "sha": "sha3", "size": 150, "mode": "100644"},
                    {"path": "src/sub/deep.py", "type": "blob", "sha": "sha4", "size": 300, "mode": "100644"},
                    {"path": "src/sub/nested/deeper.py", "type": "blob", "sha": "sha5", "size": 400, "mode": "100644"},
                ]
            }),
        ]
        result = do_list_repo_files(client, "owner", "repo", path="/src/", depth=1)
        assert result["total_count"] == 3
        paths = {item["path"] for item in result["items"]}
        assert paths == {"src/main.py", "src/utils.py", "src/sub/deep.py"}

    def test_includes_directories(self, client):
        client.request.side_effect = [
            _resp({"default_branch": "main"}),
            _resp({
                "tree": [
                    {"path": "src/main.py", "type": "blob", "sha": "sha1", "size": 100, "mode": "100644"},
                    {"path": "src/", "type": "tree", "sha": "sha2", "size": 0, "mode": "040000"},
                    {"path": "src/sub/", "type": "tree", "sha": "sha3", "size": 0, "mode": "040000"},
                ]
            }),
        ]
        result = do_list_repo_files(client, "owner", "repo")
        assert result["total_count"] == 3
        types = {item["type"] for item in result["items"]}
        assert types == {"blob", "tree"}

    def test_empty_tree(self, client):
        client.request.side_effect = [
            _resp({"default_branch": "main"}),
            _resp({"tree": []}),
        ]
        result = do_list_repo_files(client, "owner", "repo")
        assert result["total_count"] == 0
        assert result["items"] == []

    def test_invalid_path_no_leading_slash(self, client):
        with pytest.raises(RuntimeError, match="path must start with '/'"):
            do_list_repo_files(client, "owner", "repo", path="src/")

    def test_invalid_depth(self, client):
        with pytest.raises(RuntimeError, match="depth must be >= -1"):
            do_list_repo_files(client, "owner", "repo", depth=-2)
