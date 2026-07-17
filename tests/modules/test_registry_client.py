"""Tests for the HTTP-based registry client and the get_modules_repo backend dispatch."""

import json
from unittest import mock

import pytest
import requests
import responses
import yaml

import nf_core.modules.registry_client
from nf_core.components.constants import NF_CORE_MODULES_REMOTE
from nf_core.modules.modules_repo import get_modules_repo
from nf_core.modules.registry_client import COMPONENTS_JSON_URL, GITHUB_RAW_BASE, RegistryClient

LATEST_SHA = "1234567890abcdef1234567890abcdef12345678"
OLD_SHA = "fedcba0987654321fedcba0987654321fedcba09"

COMPONENTS = {
    "modules": [
        {
            "path": "modules/nf-core/samtools/index/meta.yml",
            "git_sha": LATEST_SHA,
            "files": [
                "modules/nf-core/samtools/index/main.nf",
                "modules/nf-core/samtools/index/meta.yml",
                "modules/nf-core/samtools/index/tests/main.nf.test",
            ],
            "meta": {"name": "samtools_index"},
        },
        {
            "path": "modules/nf-core/fastqc/meta.yml",
            "git_sha": LATEST_SHA,
            "files": ["modules/nf-core/fastqc/main.nf", "modules/nf-core/fastqc/meta.yml"],
            "meta": {"name": "fastqc"},
        },
    ],
    "subworkflows": [
        {
            "path": "subworkflows/nf-core/bam_sort_stats_samtools/meta.yml",
            "git_sha": LATEST_SHA,
            "files": ["subworkflows/nf-core/bam_sort_stats_samtools/main.nf"],
            "meta": {"name": "bam_sort_stats_samtools"},
        }
    ],
}


@pytest.fixture
def registry(monkeypatch, tmp_path):
    """A RegistryClient with its on-disk cache redirected to a temporary directory."""
    monkeypatch.setattr(nf_core.modules.registry_client, "NFCORE_CACHE_DIR", tmp_path)
    return RegistryClient()


def add_components_json(rsps, payload=COMPONENTS, **kwargs):
    rsps.add(responses.GET, COMPONENTS_JSON_URL, json=payload, **kwargs)


def raw_url(sha, path):
    return GITHUB_RAW_BASE.format(sha=sha, path=path)


def mock_gh_response(json_data, status_code=200):
    resp = mock.Mock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(f"{status_code} error")
    else:
        resp.raise_for_status.return_value = None
    return resp


# get_modules_repo backend dispatch


@pytest.mark.parametrize(
    "remote_url,branch",
    [
        (None, None),
        (NF_CORE_MODULES_REMOTE, None),
        (None, "master"),
        (NF_CORE_MODULES_REMOTE, "master"),
    ],
)
def test_get_modules_repo_registry_for_default_remote_and_branch(remote_url, branch):
    """The default nf-core/modules remote on its default branch uses the HTTP registry."""
    assert isinstance(get_modules_repo(remote_url, branch), RegistryClient)


@pytest.mark.parametrize(
    "remote_url,branch",
    [
        (NF_CORE_MODULES_REMOTE, "dev"),
        ("https://github.com/other/modules.git", None),
        ("https://github.com/other/modules.git", "master"),
    ],
)
def test_get_modules_repo_git_backend_for_custom_remote_or_branch(remote_url, branch):
    """Custom remotes or branches fall back to the git-backed ModulesRepo."""
    with mock.patch("nf_core.modules.modules_repo.ModulesRepo") as mock_repo:
        get_modules_repo(remote_url, branch)
        mock_repo.assert_called_once_with(remote_url=remote_url, branch=branch, no_pull=False, hide_progress=False)


# components.json fetching and caching


def test_path_to_name():
    assert RegistryClient._path_to_name("modules/nf-core/samtools/index/meta.yml", "modules") == "samtools/index"
    assert RegistryClient._path_to_name("modules/nf-core/fastqc/meta.yml", "modules") == "fastqc"
    assert (
        RegistryClient._path_to_name("subworkflows/nf-core/bam_sort_stats_samtools/meta.yml", "subworkflows")
        == "bam_sort_stats_samtools"
    )


def test_load_fetches_and_writes_cache(registry):
    with responses.RequestsMock() as rsps:
        add_components_json(rsps, headers={"ETag": 'W/"etag123"'})
        assert registry.get_avail_components("modules") == ["samtools/index", "fastqc"]
        assert registry.get_avail_components("subworkflows") == ["bam_sort_stats_samtools"]
        # No conditional header on a cold cache
        assert "If-None-Match" not in rsps.calls[0].request.headers
    assert json.loads(registry._cache_path.read_text()) == COMPONENTS
    assert registry._etag_path.read_text() == 'W/"etag123"'


def test_load_uses_cache_on_304(registry):
    registry._cache_path.parent.mkdir(parents=True, exist_ok=True)
    registry._cache_path.write_text(json.dumps(COMPONENTS))
    registry._etag_path.write_text('W/"etag123"')
    with responses.RequestsMock() as rsps:
        add_components_json(rsps, payload=None, status=304)
        assert registry.component_exists("samtools/index", "modules")
        assert rsps.calls[0].request.headers["If-None-Match"] == 'W/"etag123"'


@pytest.mark.parametrize("failure", ["connection_error", "server_error"])
def test_load_falls_back_to_cache_on_fetch_failure(registry, caplog, failure):
    """Both connection errors and HTTP errors fall back to a valid cached components.json."""
    registry._cache_path.parent.mkdir(parents=True, exist_ok=True)
    registry._cache_path.write_text(json.dumps(COMPONENTS))
    with responses.RequestsMock() as rsps:
        if failure == "connection_error":
            rsps.add(responses.GET, COMPONENTS_JSON_URL, body=requests.exceptions.ConnectionError("boom"))
        else:
            add_components_json(rsps, payload=None, status=500)
        assert registry.component_exists("fastqc", "modules")
    assert "using cached components.json" in caplog.text


@pytest.mark.parametrize("failure", ["connection_error", "server_error"])
def test_load_raises_without_cache(registry, failure):
    with responses.RequestsMock() as rsps:
        if failure == "connection_error":
            rsps.add(responses.GET, COMPONENTS_JSON_URL, body=requests.exceptions.ConnectionError("boom"))
        else:
            add_components_json(rsps, payload=None, status=500)
        with pytest.raises(LookupError, match="no local cache"):
            registry.get_avail_components("modules")


# registry lookups


def test_component_exists_and_latest_version(registry):
    with responses.RequestsMock() as rsps:
        add_components_json(rsps)
        assert registry.component_exists("samtools/index", "modules")
        assert not registry.component_exists("samtools/index", "subworkflows")
        assert not registry.component_exists("nonexistent", "modules")
        assert registry.get_latest_component_version("fastqc", "modules") == LATEST_SHA
        assert registry.get_latest_component_version("nonexistent", "modules") is None


def test_get_meta_yml(registry):
    with responses.RequestsMock() as rsps:
        add_components_json(rsps)
        meta = registry.get_meta_yml("modules", "fastqc")
        assert yaml.safe_load(meta) == {"name": "fastqc"}
        assert registry.get_meta_yml("modules", "nonexistent") is None


# component installation


def test_install_component_at_latest_sha(registry, tmp_path):
    """At the registry's latest SHA the file list from components.json is used directly."""
    install_dir = tmp_path / "install"
    with responses.RequestsMock() as rsps:
        add_components_json(rsps)
        for file_path in COMPONENTS["modules"][0]["files"]:
            rsps.add(responses.GET, raw_url(LATEST_SHA, file_path), body=f"content of {file_path}")
        assert registry.install_component("samtools/index", install_dir, LATEST_SHA, "modules")
    module_dir = install_dir / "samtools/index"
    assert (module_dir / "main.nf").read_text() == "content of modules/nf-core/samtools/index/main.nf"
    assert (module_dir / "meta.yml").is_file()
    assert (module_dir / "tests/main.nf.test").is_file()


def test_install_component_at_old_sha_lists_files_at_ref(registry, tmp_path):
    """At an older SHA the file list must come from the GitHub contents API at that ref,
    since the file set may differ from the registry's latest."""
    install_dir = tmp_path / "install"
    contents = [{"type": "file", "path": "modules/nf-core/samtools/index/main.nf"}]
    with (
        responses.RequestsMock() as rsps,
        mock.patch("nf_core.modules.registry_client.gh_api") as mock_gh,
    ):
        add_components_json(rsps)
        mock_gh.get.return_value = mock_gh_response(contents)
        rsps.add(responses.GET, raw_url(OLD_SHA, "modules/nf-core/samtools/index/main.nf"), body="old main.nf")
        assert registry.install_component("samtools/index", install_dir, OLD_SHA, "modules")
        assert mock_gh.get.call_args.kwargs["params"] == {"ref": OLD_SHA}
    module_dir = install_dir / "samtools/index"
    assert (module_dir / "main.nf").read_text() == "old main.nf"
    # meta.yml is in the latest file list but did not exist at the old SHA
    assert not (module_dir / "meta.yml").exists()


def test_install_component_recurses_into_directories(registry, tmp_path):
    install_dir = tmp_path / "install"
    listings = {
        "modules/nf-core/samtools/index": [
            {"type": "file", "path": "modules/nf-core/samtools/index/main.nf"},
            {"type": "dir", "path": "modules/nf-core/samtools/index/tests"},
        ],
        "modules/nf-core/samtools/index/tests": [
            {"type": "file", "path": "modules/nf-core/samtools/index/tests/main.nf.test"},
        ],
    }
    with (
        responses.RequestsMock() as rsps,
        mock.patch("nf_core.modules.registry_client.gh_api") as mock_gh,
    ):
        add_components_json(rsps)
        mock_gh.get.side_effect = lambda url, params=None: mock_gh_response(listings[url.split("/contents/")[1]])
        for file_path in (
            "modules/nf-core/samtools/index/main.nf",
            "modules/nf-core/samtools/index/tests/main.nf.test",
        ):
            rsps.add(responses.GET, raw_url(OLD_SHA, file_path), body="content")
        assert registry.install_component("samtools/index", install_dir, OLD_SHA, "modules")
    assert (install_dir / "samtools/index/tests/main.nf.test").is_file()


def test_install_component_cleans_up_on_failure(registry, tmp_path):
    """A failed download must not leave a partially-installed component behind."""
    install_dir = tmp_path / "install"
    with responses.RequestsMock() as rsps:
        add_components_json(rsps)
        files = COMPONENTS["modules"][1]["files"]
        rsps.add(responses.GET, raw_url(LATEST_SHA, files[0]), body="content")
        rsps.add(responses.GET, raw_url(LATEST_SHA, files[1]), status=500)
        assert not registry.install_component("fastqc", install_dir, LATEST_SHA, "modules")
    assert not (install_dir / "fastqc").exists()


def test_install_component_unknown_at_latest(registry, tmp_path):
    """A component the contents API can't list either reports failure."""
    with (
        responses.RequestsMock() as rsps,
        mock.patch("nf_core.modules.registry_client.gh_api") as mock_gh,
    ):
        add_components_json(rsps)
        mock_gh.get.return_value = mock_gh_response({"message": "Not Found"}, status_code=404)
        assert not registry.install_component("nonexistent", tmp_path, LATEST_SHA, "modules")


# file comparison


def test_component_files_identical(registry, tmp_path):
    (tmp_path / "main.nf").write_text("process FOO {}")
    (tmp_path / "meta.yml").write_text("name: foo")
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, raw_url(LATEST_SHA, "modules/nf-core/foo/main.nf"), body="process FOO {}")
        rsps.add(responses.GET, raw_url(LATEST_SHA, "modules/nf-core/foo/meta.yml"), body="name: bar")
        result = registry.component_files_identical("foo", tmp_path, LATEST_SHA, "modules")
    assert result == {"main.nf": True, "meta.yml": False}


def test_component_files_identical_skips_missing_files(registry, tmp_path):
    """Files missing locally or on the remote are skipped (left as identical), mirroring SyncedRepo."""
    (tmp_path / "main.nf").write_text("process FOO {}")
    # meta.yml missing locally; main.nf missing on the remote at this commit
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, raw_url(OLD_SHA, "modules/nf-core/foo/main.nf"), status=404)
        result = registry.component_files_identical("foo", tmp_path, OLD_SHA, "modules")
    assert result == {"main.nf": True, "meta.yml": True}


def test_component_files_identical_network_failure_is_not_identical(registry, tmp_path, caplog):
    """A network failure must report 'not identical' instead of silently matching."""
    (tmp_path / "main.nf").write_text("process FOO {}")
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            raw_url(LATEST_SHA, "modules/nf-core/foo/main.nf"),
            body=requests.exceptions.ConnectionError("boom"),
        )
        result = registry.component_files_identical("foo", tmp_path, LATEST_SHA, "modules")
    assert result["main.nf"] is False
    assert "Could not fetch" in caplog.text


# git log and SHA checks via the GitHub API


def test_get_component_git_log_paginates():
    registry = RegistryClient()
    page1 = [{"sha": f"sha{i}", "commit": {"message": f"commit {i}"}} for i in range(100)]
    page2 = [{"sha": f"sha{i}", "commit": {"message": f"commit {i}"}} for i in range(100, 130)]
    with mock.patch("nf_core.modules.registry_client.gh_api") as mock_gh:
        mock_gh.get.side_effect = [mock_gh_response(page1), mock_gh_response(page2)]
        commits = registry.get_component_git_log("fastqc", "modules")
    assert len(commits) == 130
    assert commits[0] == {"git_sha": "sha0", "trunc_message": "commit 0"}
    pages = [call.kwargs["params"]["page"] for call in mock_gh.get.call_args_list]
    assert pages == [1, 2]


def test_get_component_git_log_respects_depth():
    registry = RegistryClient()
    page1 = [{"sha": f"sha{i}", "commit": {"message": f"commit {i}"}} for i in range(100)]
    with mock.patch("nf_core.modules.registry_client.gh_api") as mock_gh:
        mock_gh.get.return_value = mock_gh_response(page1)
        commits = registry.get_component_git_log("fastqc", "modules", depth=5)
    assert len(commits) == 5
    assert mock_gh.get.call_count == 1


@pytest.mark.parametrize(
    "status,compare_status,expected",
    [
        (200, "behind", True),
        (200, "identical", True),
        (200, "ahead", False),
        (200, "diverged", False),
        (404, None, False),
    ],
)
def test_sha_exists_on_branch(status, compare_status, expected):
    registry = RegistryClient()
    with mock.patch("nf_core.modules.registry_client.gh_api") as mock_gh:
        mock_gh.get.return_value = mock_gh_response({"status": compare_status}, status_code=status)
        assert registry.sha_exists_on_branch(LATEST_SHA) is expected


# single-file fetching (used for schema loading in lint)


def test_get_file_content_is_memoized(registry):
    url = raw_url("master", "modules/meta-schema.json")
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, url, body='{"type": "object"}')
        assert registry.get_file_content("modules/meta-schema.json") == '{"type": "object"}'
        assert registry.get_file_content("modules/meta-schema.json") == '{"type": "object"}'
        assert len(rsps.calls) == 1
