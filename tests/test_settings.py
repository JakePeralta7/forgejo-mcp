import pytest

from forgejo_mcp.server import Settings, env_bool, load_settings


def base_env(**overrides):
    env = {
        "FORGEJO_URL": "https://codeberg.org",
        "FORGEJO_ACCESS_TOKEN": "secret",
    }
    env.update(overrides)
    return {k: v for k, v in env.items() if v is not None}


class TestLoadSettings:
    def test_defaults(self):
        s = load_settings(base_env())
        assert s == Settings(
            url="https://codeberg.org",
            access_token="secret",
            user_agent="forgejo-mcp/0.1.0",
            timeout=30.0,
            tls_insecure=False,
        )

    def test_full_custom(self):
        s = load_settings(
            base_env(
                FORGEJO_USER_AGENT="my-agent/9.9",
                FORGEJO_TIMEOUT="60",
                FORGEJO_TLS_INSECURE="true",
            )
        )
        assert s.user_agent == "my-agent/9.9"
        assert s.timeout == 60.0
        assert s.tls_insecure is True

    def test_url_trailing_slash_stripped(self):
        s = load_settings(base_env(FORGEJO_URL="https://codeberg.org/"))
        assert s.url == "https://codeberg.org"

    def test_blank_optional_user_agent_defaults(self):
        s = load_settings(base_env(FORGEJO_USER_AGENT="   "))
        assert s.user_agent == "forgejo-mcp/0.1.0"

    def test_missing_url_raises(self):
        with pytest.raises(RuntimeError, match="FORGEJO_URL"):
            load_settings({"FORGEJO_ACCESS_TOKEN": "secret"})

    def test_missing_token_raises(self):
        with pytest.raises(RuntimeError, match="FORGEJO_ACCESS_TOKEN"):
            load_settings({"FORGEJO_URL": "https://codeberg.org"})

    def test_blank_url_raises(self):
        with pytest.raises(RuntimeError, match="FORGEJO_URL"):
            load_settings(base_env(FORGEJO_URL="  "))

    @pytest.mark.parametrize("value", ["true", "TRUE", "1", "Yes", "on"])
    def test_bool_true_variants(self, value):
        assert load_settings(base_env(FORGEJO_TLS_INSECURE=value)).tls_insecure is True

    @pytest.mark.parametrize("value", ["false", "FALSE", "0", "No", "off"])
    def test_bool_false_variants(self, value):
        assert load_settings(base_env(FORGEJO_TLS_INSECURE=value)).tls_insecure is False

    def test_invalid_bool_raises(self):
        with pytest.raises(RuntimeError, match="FORGEJO_TLS_INSECURE"):
            load_settings(base_env(FORGEJO_TLS_INSECURE="maybe"))

    def test_invalid_timeout_raises(self):
        with pytest.raises(RuntimeError, match="FORGEJO_TIMEOUT"):
            load_settings(base_env(FORGEJO_TIMEOUT="abc"))

    def test_nonpositive_timeout_raises(self):
        with pytest.raises(RuntimeError, match="FORGEJO_TIMEOUT"):
            load_settings(base_env(FORGEJO_TIMEOUT="0"))


class TestEnvBool:
    def test_unset_returns_default(self):
        assert env_bool("NOPE", {}, True) is True
        assert env_bool("NOPE", {}, False) is False

    def test_blank_returns_default(self):
        assert env_bool("NOPE", {"NOPE": ""}, True) is True


def test_settings_frozen():
    s = load_settings(base_env())
    with pytest.raises(Exception):
        s.url = "other"  # type: ignore[misc]
