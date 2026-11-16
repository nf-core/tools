"""Tests for the detached remote-version cache updater."""

import json
import subprocess
import sys
from unittest import mock

import pytest
from packaging.version import InvalidVersion

import nf_core.utils
from nf_core.version_updater import refresh_version_cache


def test_refresh_version_cache(tmp_path):
    """A valid remote version is written to the cache atomically."""
    remote_version_path = tmp_path / "remote_version"
    remote_version_path.write_text("4.1.0\n")
    cache_path = tmp_path / "latest_version.json"

    refresh_version_cache(remote_version_path.as_uri(), cache_path)

    cached = json.loads(cache_path.read_text())
    assert cached["version"] == "4.1.0"
    assert isinstance(cached["timestamp"], float)


def test_refresh_version_cache_rejects_invalid_version(tmp_path):
    """A malformed response does not replace an existing valid cache."""
    remote_version_path = tmp_path / "remote_version"
    remote_version_path.write_text("not a version")
    cache_path = tmp_path / "latest_version.json"
    original_cache = '{"version": "4.0.0", "timestamp": 123}'
    cache_path.write_text(original_cache)

    with pytest.raises(InvalidVersion):
        refresh_version_cache(remote_version_path.as_uri(), cache_path)

    assert cache_path.read_text() == original_cache


def test_spawn_remote_version_refresh_uses_updater_module(tmp_path, monkeypatch):
    """The parent process launches the updater without embedding Python source."""
    cache_path = tmp_path / "latest_version.json"
    monkeypatch.setattr(nf_core.utils, "NFCORE_CACHE_DIR", tmp_path)
    monkeypatch.setattr(nf_core.utils, "REMOTE_VERSION_CACHE", cache_path)

    with mock.patch("subprocess.Popen") as popen:
        nf_core.utils._spawn_remote_version_refresh("https://example.com/tools_version?v=4.0.0")

    popen.assert_called_once_with(
        [
            sys.executable,
            "-m",
            "nf_core.version_updater",
            "https://example.com/tools_version?v=4.0.0",
            str(cache_path),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
