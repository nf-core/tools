"""GitHub auth warning regressions: supplied, gh-cli, token and missing credentials."""
from unittest.mock import patch

import requests.auth

from nf_core.github_api import GitHubAPISession


def fresh_session():
    # Auth is initialized by requests_cache during lazy_init in production.
    # Avoid network/cache setup while exercising this pure auth-choice logic.
    session = GitHubAPISession()
    session.auth = None
    return session


def test_gh_cli_credentials_do_not_trigger_missing_auth_warning(tmp_path, monkeypatch):
    hosts = tmp_path / ".config" / "gh"
    hosts.mkdir(parents=True)
    (hosts / "hosts.yml").write_text(
        "github.com:\n  user: example\n  oauth_token: test-token\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("nf_core.github_api.Path.home", lambda: tmp_path)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    session = fresh_session()
    with patch("nf_core.github_api.log.warning") as warning:
        session.setup_github_auth()

    assert isinstance(session.auth, requests.auth.HTTPBasicAuth)
    assert session.auth_mode == "gh CLI config: example"
    warning.assert_not_called()


def test_environment_token_is_accepted_without_warning(tmp_path, monkeypatch):
    monkeypatch.setattr("nf_core.github_api.Path.home", lambda: tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")

    session = fresh_session()
    with patch("nf_core.github_api.log.warning") as warning:
        session.setup_github_auth()

    assert session.auth_mode == "Bearer token with GITHUB_TOKEN"
    assert session.auth is not None
    warning.assert_not_called()


def test_supplied_auth_takes_precedence_over_environment(tmp_path, monkeypatch):
    monkeypatch.setattr("nf_core.github_api.Path.home", lambda: tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    supplied = object()

    session = fresh_session()
    with patch("nf_core.github_api.log.warning") as warning:
        session.setup_github_auth(supplied)

    assert session.auth is supplied
    assert session.auth_mode == "supplied to function"
    warning.assert_not_called()


def test_missing_and_empty_tokens_provide_actionable_guidance(tmp_path, monkeypatch):
    monkeypatch.setattr("nf_core.github_api.Path.home", lambda: tmp_path)
    for token in (None, ""):
        if token is None:
            monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        else:
            monkeypatch.setenv("GITHUB_TOKEN", token)
        session = fresh_session()
        with patch("nf_core.github_api.log.warning") as warning:
            session.setup_github_auth()
        assert session.auth is None
        warning.assert_called_once()
        message = warning.call_args.args[0]
        assert "gh auth login" in message
        assert "https://cli.github.com/manual/gh_auth_login" in message
        assert "GITHUB_TOKEN" in message
