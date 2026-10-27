"""Malformed GitHub CLI config should not block environment-token fallback."""

from unittest.mock import patch

import pytest

from nf_core.github_api import GitHubAPISession


@pytest.mark.parametrize("contents", ["", "[]\n", "github.com: []\n", "github.com: {}\n"])
def test_malformed_hosts_yaml_falls_back_to_env_token(tmp_path, monkeypatch, contents):
    path = tmp_path / ".config" / "gh" / "hosts.yml"
    path.parent.mkdir(parents=True)
    path.write_text(contents)
    monkeypatch.setattr("nf_core.github_api.Path.home", lambda: tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "fallback-token")
    session = GitHubAPISession()
    session.auth = None

    with patch("nf_core.github_api.log.warning") as warning:
        session.setup_github_auth()
    assert session.auth_mode == "Bearer token with GITHUB_TOKEN"
    assert session.auth.token == "fallback-token"
    warning.assert_not_called()
