"""Offline regressions for nf-core/tools #4613 and #4584."""

from __future__ import annotations

import json
import socket
import subprocess
from pathlib import Path
from unittest import mock

import git
import pytest
import requests
import requests_cache
from click.testing import CliRunner

import nf_core.__main__
import nf_core.modules.lint
import nf_core.modules.modules_repo
import nf_core.pipelines.lint
import nf_core.subworkflows.lint
from nf_core import __version__
from nf_core.modules.modules_repo import ModulesRepo
from nf_core.synced_repo import SyncedRepo


@pytest.fixture(autouse=True)
def offline_config(monkeypatch, tmp_path):
    """Isolate NFCORE_DIR, reset global repo pull state, and block real TCP sockets."""
    nfcore_dir = tmp_path / "nfcore_config"
    nfcore_dir.mkdir()
    monkeypatch.setattr("nf_core.utils.NFCORE_DIR", nfcore_dir)
    monkeypatch.setattr("nf_core.modules.modules_repo.NFCORE_DIR", nfcore_dir)
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file")
    monkeypatch.setenv("NFCORE_NO_VERSION_CHECK", "1")

    monkeypatch.setattr(ModulesRepo, "no_pull_global", False)
    monkeypatch.setattr(SyncedRepo, "local_repo_statuses", {})
    monkeypatch.setattr("nf_core.utils.fetch_wf_config", _mock_wf_config)
    monkeypatch.setattr(
        "nf_core.components.nfcore_component.NFCoreComponent.get_container_with_inspect",
        lambda *args, **kwargs: None,
    )

    def _blocked_socket(*args, **kwargs):
        raise OSError("Real network sockets are blocked in offline tests")

    monkeypatch.setattr(socket.socket, "connect", _blocked_socket)
    monkeypatch.setattr(socket.socket, "connect_ex", _blocked_socket)
    monkeypatch.setattr(socket, "create_connection", _blocked_socket)

    with requests_cache.disabled():
        yield nfcore_dir


def _create_minimal_pipeline(
    base_dir: Path,
    *,
    with_local_module: bool = False,
    with_remote_module: bool = False,
    with_local_subworkflow: bool = False,
    with_remote_subworkflow: bool = False,
    with_workflow_yml: bool = False,
    remote_sha: str | None = None,
) -> Path:
    """Create a minimal local pipeline directory without hitting any network."""
    pipeline_dir = base_dir / "testpipeline"
    pipeline_dir.mkdir(parents=True, exist_ok=True)

    (pipeline_dir / ".nf-core.yml").write_text(
        f"repository_type: pipeline\nnf_core_version: {__version__}\n",
        encoding="utf-8",
    )
    (pipeline_dir / "main.nf").write_text("workflow {\n    println 'hello'\n}\n", encoding="utf-8")
    (pipeline_dir / "nextflow.config").touch()
    (pipeline_dir / "modules").mkdir(exist_ok=True)

    modules_json: dict = {
        "name": "nf-core/testpipeline",
        "homePage": "https://github.com/nf-core/testpipeline",
        "repos": {},
    }

    if with_local_module:
        local_mod = pipeline_dir / "modules" / "local" / "mytool"
        local_mod.mkdir(parents=True)
        (local_mod / "main.nf").write_text(
            """process MYTOOL {
    label 'process_single'
    conda "${moduleDir}/environment.yml"
    container "quay.io/biocontainers/mytool:1.0.0--0"

    input:
    tuple val(meta), path(reads)

    output:
    tuple val(meta), path("*.txt"), emit: txt
    tuple val("${task.process}"), val('mytool'), eval('mytool --version'), topic: versions, emit: versions_mytool

    when:
    task.ext.when == null || task.ext.when

    script:
    def prefix = task.ext.prefix ?: "${meta.id}"
    \"\"\"
    touch ${prefix}.txt
    \"\"\"
}
""",
            encoding="utf-8",
        )
        (local_mod / "environment.yml").write_text(
            "---\n"
            "# yaml-language-server: $schema=https://raw.githubusercontent.com/nf-core/modules/master/modules/environment-schema.json\n"
            "channels:\n"
            "  - conda-forge\n"
            "  - bioconda\n"
            "dependencies:\n"
            "  - bioconda::mytool=1.0.0\n",
            encoding="utf-8",
        )
        (local_mod / "meta.yml").write_text(
            """name: mytool
tools:
  - mytool:
      description: Test tool
authors: ['@testuser']
""",
            encoding="utf-8",
        )

    if with_remote_module:
        remote_mod = pipeline_dir / "modules" / "nf-core" / "mytool"
        remote_mod.mkdir(parents=True)
        (remote_mod / "main.nf").write_text(
            "process MYTOOL {\n    output:\n    val 1, emit: out\n    script:\n    'echo hi'\n}\n",
            encoding="utf-8",
        )
        (remote_mod / "meta.yml").write_text("name: mytool\n", encoding="utf-8")
        modules_json["repos"].setdefault("https://github.com/nf-core/modules.git", {})["modules"] = {
            "nf-core": {
                "mytool": {
                    "branch": "master",
                    "git_sha": remote_sha or "deadbeef" * 5,
                    "installed_by": ["modules"],
                }
            }
        }

    subwf_main_nf = """include { MYTOOL as TOOL_A } from '../../../modules/local/mytool/main'
include { MYTOOL as TOOL_B } from '../../../modules/local/mytool/main'

workflow MYSUBWF {
    take:
    ch_input

    main:
    TOOL_A(ch_input)
    TOOL_B(TOOL_A.out.txt)

    emit:
    txt = TOOL_B.out.txt
}
"""
    subwf_meta_yml = """name: mysubwf
input:
  - ch_input:
      description: Input channel
output:
  - txt:
      description: Output channel
authors: ['@testuser']
"""

    if with_local_subworkflow:
        local_subwf = pipeline_dir / "subworkflows" / "local" / "mysubwf"
        local_subwf.mkdir(parents=True)
        (local_subwf / "main.nf").write_text(subwf_main_nf, encoding="utf-8")
        (local_subwf / "meta.yml").write_text(subwf_meta_yml, encoding="utf-8")

    if with_remote_subworkflow:
        remote_subwf = pipeline_dir / "subworkflows" / "nf-core" / "mysubwf"
        remote_subwf.mkdir(parents=True)
        (remote_subwf / "main.nf").write_text(subwf_main_nf, encoding="utf-8")
        (remote_subwf / "meta.yml").write_text(subwf_meta_yml, encoding="utf-8")
        modules_json["repos"].setdefault("https://github.com/nf-core/modules.git", {})["subworkflows"] = {
            "nf-core": {
                "mysubwf": {
                    "branch": "master",
                    "git_sha": remote_sha or "deadbeef" * 5,
                    "installed_by": ["subworkflows"],
                }
            }
        }

    (pipeline_dir / "modules.json").write_text(json.dumps(modules_json, indent=4), encoding="utf-8")

    if with_workflow_yml:
        wf_dir = pipeline_dir / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yml").write_text(
            "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n",
            encoding="utf-8",
        )

    return pipeline_dir


def _create_cached_modules_repo(nfcore_dir: Path, *, with_module: bool = False) -> tuple[Path, str]:
    """Create a local bare/cached git repo at NFCORE_DIR/nf-core/modules with schemas and tracking branch."""
    remote_bare = nfcore_dir / "_bare_origin.git"
    git.Repo.init(remote_bare, bare=True, initial_branch="master")

    work_dir = nfcore_dir / "_seed_work"
    seed_repo = git.Repo.init(work_dir, initial_branch="master")
    with seed_repo.config_writer() as cfg:
        cfg.set_value("user", "name", "Test User")
        cfg.set_value("user", "email", "test@example.com")

    (work_dir / ".nf-core.yml").write_text("repository_type: modules\norg_path: nf-core\n", encoding="utf-8")
    (work_dir / "modules" / "nf-core").mkdir(parents=True)
    (work_dir / "modules" / "meta-schema.json").write_text('{"type": "object"}', encoding="utf-8")
    (work_dir / "modules" / "environment-schema.json").write_text('{"type": "object"}', encoding="utf-8")
    (work_dir / "subworkflows" / "nf-core").mkdir(parents=True)
    (work_dir / "subworkflows" / "yaml-schema.json").write_text('{"type": "object"}', encoding="utf-8")
    if with_module:
        mod_dir = work_dir / "modules" / "nf-core" / "mytool"
        mod_dir.mkdir(parents=True)
        (mod_dir / "main.nf").write_text(
            "process MYTOOL {\n    output:\n    val 1, emit: out\n    script:\n    'echo hi'\n}\n",
            encoding="utf-8",
        )
        (mod_dir / "meta.yml").write_text("name: mytool\n", encoding="utf-8")

    seed_repo.index.add(["."])
    commit = seed_repo.index.commit("initial modules commit")
    seed_repo.create_remote("origin", str(remote_bare))
    seed_repo.remotes.origin.push("master:master")

    cache_dir = nfcore_dir / "nf-core" / "modules"
    cache_dir.parent.mkdir(parents=True, exist_ok=True)
    git.Repo.clone_from(str(remote_bare), cache_dir)
    return cache_dir, commit.hexsha


def _mock_wf_config(*args, **kwargs) -> dict:
    return {
        "manifest": {
            "name": "nf-core/testpipeline",
            "author": "Test Author",
            "homePage": "https://github.com/nf-core/testpipeline",
            "description": "Offline test pipeline",
            "mainScript": "main.nf",
            "nextflowVersion": "!>=25.10.4",
            "version": "1.0.0dev",
        },
        "params": {"input": None, "outdir": None},
    }


@pytest.mark.parametrize("group_options", [[], ["--no-pull"]], ids=["default", "no_pull"])
def test_modules_lint_local_offline_no_cache_does_not_clone(tmp_path, group_options):
    """Issue #4613: `nf-core modules lint -d modules/local --local` must not clone nf-core/modules."""
    pipeline_dir = _create_minimal_pipeline(tmp_path, with_local_module=True)
    (pipeline_dir / "modules.json").write_text("{broken")
    runner = CliRunner()

    with (
        mock.patch("git.Repo.clone_from", side_effect=git.GitCommandError("git clone", 128)) as mock_clone,
        mock.patch("git.Remote.fetch", side_effect=git.GitCommandError("git fetch", 128)) as mock_fetch,
        mock.patch("requests.get", side_effect=requests.exceptions.ConnectionError("offline")),
    ):
        result = runner.invoke(
            nf_core.__main__.nf_core_cli,
            ["modules", *group_options, "lint", "-d", str(pipeline_dir / "modules" / "local"), "--local"],
        )

    assert result.exit_code == 0, f"CLI exited {result.exit_code}:\n{result.output}"
    mock_clone.assert_not_called()
    mock_fetch.assert_not_called()
    assert (pipeline_dir / "modules.json").read_text() == "{broken"


def test_modules_lint_local_offline_with_existing_cache_does_not_fetch(tmp_path, offline_config):
    """Issue #4613: `modules lint --local` with an existing cache must not fetch or prompt to delete it."""
    nfcore_dir = offline_config
    cache_dir, _ = _create_cached_modules_repo(nfcore_dir)
    pipeline_dir = _create_minimal_pipeline(tmp_path, with_local_module=True)

    with (
        mock.patch("git.Remote.fetch", side_effect=git.GitCommandError("git fetch", 128)) as mock_fetch,
        mock.patch("rich.prompt.Confirm.ask", side_effect=AssertionError("Should not prompt to delete cache")),
        mock.patch("requests.get", side_effect=requests.exceptions.ConnectionError("offline")),
    ):
        module_lint = nf_core.modules.lint.ModuleLint(directory=pipeline_dir)
        module_lint.lint(print_results=False, local=True)

    mock_fetch.assert_not_called()
    assert cache_dir.exists()
    assert len(module_lint.failed) == 0
    passed_names = {r.lint_test for r in module_lint.passed}
    assert "meta_yml_valid" in passed_names
    assert "environment_yml_valid" in passed_names


@pytest.mark.parametrize("author_options", [["--author", "@testuser"], []], ids=["explicit", "prompt"])
def test_modules_no_pull_create_offline(tmp_path, author_options):
    """Issue #4613: `nf-core modules --no-pull create` must succeed offline without calling GitHub or git."""
    pipeline_dir = _create_minimal_pipeline(tmp_path)
    git.Repo.init(pipeline_dir)
    legacy_module = pipeline_dir / "modules/nf-core/modules/existing/main.nf"
    legacy_module.parent.mkdir(parents=True)
    legacy_module.write_text("// Existing module in legacy directory\n")
    runner = CliRunner()

    with (
        mock.patch("nf_core.utils.is_interactive", return_value=True),
        mock.patch("nf_core.components.create.run_prettier_on_file") as mock_prettier,
        mock.patch("nf_core.components.create.rich.prompt.Prompt.ask", return_value="@testuser") as mock_author,
        mock.patch("git.Repo.clone_from", side_effect=git.GitCommandError("git clone", 128)) as mock_clone,
        mock.patch("git.Remote.fetch", side_effect=git.GitCommandError("git fetch", 128)) as mock_fetch,
        mock.patch(
            "nf_core.components.create.subprocess.check_output",
            side_effect=subprocess.CalledProcessError(1, ["gh", "api", "/user"]),
        ) as mock_gh,
        mock.patch("requests.get", side_effect=requests.exceptions.ConnectionError("offline")),
        mock.patch("nf_core.components.create.rich.prompt.Confirm.ask", return_value=False),
    ):
        result = runner.invoke(
            nf_core.__main__.nf_core_cli,
            [
                "modules",
                "--no-pull",
                "create",
                "mytool",
                "-d",
                str(pipeline_dir),
                *author_options,
                "--label",
                "process_single",
                "--meta",
            ],
        )

    assert result.exit_code == 0, f"CLI exited {result.exit_code}:\n{result.output}"
    mock_clone.assert_not_called()
    mock_fetch.assert_not_called()
    mock_gh.assert_not_called()
    mock_prettier.assert_not_called()
    assert mock_author.call_count == (0 if author_options else 1)
    assert legacy_module.is_file()
    assert (pipeline_dir / "modules" / "local" / "mytool" / "main.nf").exists()
    assert (pipeline_dir / "modules" / "local" / "mytool" / "meta.yml").exists()
    assert (pipeline_dir / "modules" / "local" / "mytool" / "environment.yml").exists()


@pytest.mark.parametrize("changed", [False, True], ids=["matching_files", "changed_file"])
def test_modules_no_pull_lint_remote_offline_with_cache(tmp_path, offline_config, changed):
    """Issue #4613: `nf-core modules --no-pull lint` must use local cache without calling `git fetch`."""
    nfcore_dir = offline_config
    cache, sha = _create_cached_modules_repo(nfcore_dir, with_module=True)
    pipeline_dir = _create_minimal_pipeline(tmp_path, with_remote_module=True, remote_sha=sha)
    main_nf = Path("modules/nf-core/mytool/main.nf")
    assert (pipeline_dir / main_nf).read_bytes() == (cache / main_nf).read_bytes()
    if changed:
        (pipeline_dir / main_nf).write_text("// Local change\n")
    runner = CliRunner()

    with (
        mock.patch("git.Remote.fetch", side_effect=git.GitCommandError("git fetch", 128)) as mock_fetch,
    ):
        result = runner.invoke(
            nf_core.__main__.nf_core_cli,
            [
                "modules",
                "--no-pull",
                "lint",
                "-d",
                str(pipeline_dir),
                "--all",
                "-k",
                "module_version",
                "-k",
                "module_changes",
            ],
        )

    assert result.exit_code == int(changed), result.output
    mock_fetch.assert_not_called()
    if changed:
        assert isinstance(result.exception, SystemExit), repr(result.exception)


def test_modules_lint_remote_offline_no_cache_warns(tmp_path):
    """Issue #4613 / #4584: Remote module version/changes lint warns rather than failing/crashing when offline."""
    pipeline_dir = _create_minimal_pipeline(tmp_path, with_remote_module=True)

    with (
        mock.patch("git.Repo.clone_from", side_effect=git.GitCommandError("git clone", 128)) as mock_clone,
    ):
        module_lint = nf_core.modules.lint.ModuleLint(directory=pipeline_dir, no_pull=True)
        module_lint.lint(
            all_modules=True,
            key=("module_version", "module_changes"),
            print_results=False,
        )

    mock_clone.assert_not_called()
    assert len(module_lint.failed) == 0, f"Unexpected failures: {[r.__dict__ for r in module_lint.failed]}"
    warned_tests = {r.lint_test for r in module_lint.warned}
    assert "module_version" in warned_tests
    assert "check_local_copy" in warned_tests


def test_modules_repo_fetch_error_offline_does_not_prompt_delete(offline_config):
    """When `git fetch` fails offline, ModulesRepo must raise LookupError without deleting the local cache."""
    nfcore_dir = offline_config
    cache_dir, _ = _create_cached_modules_repo(nfcore_dir)

    with (
        mock.patch("git.Remote.fetch", side_effect=git.GitCommandError("git fetch", 128)),
        mock.patch("rich.prompt.Confirm.ask", side_effect=AssertionError("Should not prompt to delete cache")),
        pytest.raises(LookupError),
    ):
        ModulesRepo()

    assert cache_dir.exists()


@pytest.mark.parametrize(
    "exc",
    [
        requests.exceptions.SSLError("CERTIFICATE_VERIFY_FAILED"),
        requests.exceptions.ConnectionError("Failed to resolve 'www.schemastore.org'"),
        requests.exceptions.Timeout("Read timed out"),
    ],
    ids=["ssl_error", "connection_error", "timeout"],
)
def test_actions_schema_validation_offline_warns(tmp_path, exc):
    """Issue #4584: actions_schema_validation warns instead of crashing on SSL/connection/timeout errors."""
    pipeline_dir = _create_minimal_pipeline(tmp_path, with_workflow_yml=True)
    lint_obj = nf_core.pipelines.lint.PipelineLint(pipeline_dir)

    with (
        mock.patch("nf_core.pipelines.lint.actions_schema_validation.requests.get", side_effect=exc),
    ):
        results = lint_obj.actions_schema_validation()

    assert results["failed"] == []
    assert len(results["warned"]) == 1
    assert "schemastore.org" in results["warned"][0]


def test_actions_schema_validation_non_json_proxy_response_warns(tmp_path):
    """Issue #4584: Corporate proxy HTML block page (HTTP 200 non-JSON) warns instead of crashing."""
    pipeline_dir = _create_minimal_pipeline(tmp_path, with_workflow_yml=True)
    lint_obj = nf_core.pipelines.lint.PipelineLint(pipeline_dir)

    bad_response = mock.Mock()
    bad_response.status_code = 200
    bad_response.json.side_effect = requests.exceptions.JSONDecodeError("Expecting value", "<html>blocked</html>", 0)

    with (
        mock.patch("nf_core.pipelines.lint.actions_schema_validation.requests.get", return_value=bad_response),
    ):
        results = lint_obj.actions_schema_validation()

    assert results["failed"] == []
    assert len(results["warned"]) == 1
    assert "schemastore.org" in results["warned"][0]


def test_pipelines_lint_run_linting_offline_warns_without_crashing(tmp_path):
    """Issue #4584: `nf-core pipelines lint` completes offline with warnings instead of crashing."""
    pipeline_dir = _create_minimal_pipeline(tmp_path, with_remote_module=True, with_workflow_yml=True)

    with (
        mock.patch(
            "nf_core.pipelines.lint.actions_schema_validation.requests.get",
            side_effect=requests.exceptions.SSLError("corporate VPN cert error"),
        ),
        mock.patch("git.Repo.clone_from", side_effect=git.GitCommandError("git clone", 128)),
    ):
        lint_obj, module_lint_obj, _ = nf_core.pipelines.lint.run_linting(
            pipeline_dir,
            release_mode=False,
            key=("actions_schema_validation", "module_version", "module_changes"),
            hide_progress=True,
        )

    assert len(lint_obj.failed) == 0
    assert any(test_name == "actions_schema_validation" for test_name, _ in lint_obj.warned)
    assert module_lint_obj is not None
    assert len(module_lint_obj.failed) == 0
    warned_mod_tests = {r.lint_test for r in module_lint_obj.warned}
    assert "module_version" in warned_mod_tests
    assert "check_local_copy" in warned_mod_tests


def test_update_meta_yml_fix_offline_when_biotools_unreachable(tmp_path, offline_config):
    """`modules lint --fix` must not raise TypeError when bio.tools is unreachable offline."""
    nfcore_dir = offline_config
    _create_cached_modules_repo(nfcore_dir)
    pipeline_dir = _create_minimal_pipeline(tmp_path, with_local_module=True)

    with (
        mock.patch("nf_core.modules.lint.run_prettier_on_file"),
        mock.patch(
            "nf_core.components.components_utils.requests.get",
            side_effect=requests.exceptions.ConnectionError("offline"),
        ),
        mock.patch.object(ModulesRepo, "no_pull_global", True),
    ):
        module_lint = nf_core.modules.lint.ModuleLint(directory=pipeline_dir, fix=True)
        mod = module_lint.all_local_components[0]
        module_lint._safe_parse_main_nf(mod)
        module_lint.update_meta_yml_file(mod)

    assert "identifier" not in mod.meta_yml.read_text()


@pytest.mark.parametrize("requirements", [["jobs"], ["jobs", "permissions"]], ids=["valid", "invalid"])
def test_actions_schema_validation_reachable_schema(tmp_path, requirements):
    pipeline = _create_minimal_pipeline(tmp_path, with_workflow_yml=True)
    lint = nf_core.pipelines.lint.PipelineLint(pipeline)
    response = requests.Response()
    response.status_code = 200
    response._content = json.dumps({"type": "object", "required": requirements}).encode()

    with mock.patch("requests.get", return_value=response) as get:
        results = lint.actions_schema_validation()

    get.assert_called_once()
    assert get.call_args.args[0] == "https://www.schemastore.org/github-workflow"
    assert not results["warned"]
    if "permissions" in requirements:
        assert any("'permissions' is a required property" in failure for failure in results["failed"])
    else:
        assert results["passed"] == ["Workflow validation passed: ci.yml"]
        assert not results["failed"]


def test_actions_schema_validation_no_workflows(tmp_path):
    lint = nf_core.pipelines.lint.PipelineLint(_create_minimal_pipeline(tmp_path))
    with mock.patch("requests.get", side_effect=requests.ConnectionError("offline")) as get:
        results = lint.actions_schema_validation()

    get.assert_not_called()
    assert results == {"passed": [], "failed": [], "warned": []}


def test_pipelines_lint_offline_ls_remote_during_reconciliation(
    tmp_path,
    offline_config,
    caplog,
):
    _, sha = _create_cached_modules_repo(offline_config, with_module=True)
    pipeline = _create_minimal_pipeline(tmp_path, with_remote_module=True, remote_sha=sha)
    manifest = pipeline / "modules.json"
    manifest.rename(pipeline / "modules.json.saved")
    with (
        mock.patch(
            "git.Git.ls_remote", create=True, side_effect=git.GitCommandError("git ls-remote", 128)
        ) as ls_remote,
    ):
        lint, _, _ = nf_core.pipelines.lint.run_linting(
            pipeline, release_mode=False, key=("module_version",), hide_progress=True
        )

    ls_remote.assert_called()
    assert not lint.failed
    assert "Could not reconcile modules.json" in caplog.text
    assert not manifest.exists()


@pytest.mark.parametrize("group_options", [[], ["--no-pull"]], ids=["default", "no_pull"])
def test_subworkflows_lint_local_offline_no_cache_does_not_clone(tmp_path, group_options):
    """`nf-core subworkflows lint --local` must not clone/fetch, must preserve modules.json, and warns when uncached."""
    pipeline_dir = _create_minimal_pipeline(tmp_path, with_local_subworkflow=True)
    (pipeline_dir / "modules.json").write_text("{broken")
    runner = CliRunner()

    with (
        mock.patch("git.Repo.clone_from", side_effect=git.GitCommandError("git clone", 128)) as mock_clone,
        mock.patch("git.Remote.fetch", side_effect=git.GitCommandError("git fetch", 128)) as mock_fetch,
        mock.patch("requests.get", side_effect=requests.exceptions.ConnectionError("offline")),
    ):
        result = runner.invoke(
            nf_core.__main__.nf_core_cli,
            ["subworkflows", *group_options, "lint", "-d", str(pipeline_dir), "--local", "--plain-text"],
        )

    assert result.exit_code == 0, f"CLI exited {result.exit_code}:\n{result.output}"
    mock_clone.assert_not_called()
    mock_fetch.assert_not_called()
    assert (pipeline_dir / "modules.json").read_text() == "{broken"
    assert "Could not load meta.yml schema" in result.output


def test_subworkflows_lint_local_offline_with_existing_cache_does_not_fetch(tmp_path, offline_config):
    """`subworkflows lint --local` with an existing cache uses the disk schema without fetching."""
    nfcore_dir = offline_config
    cache_dir, _ = _create_cached_modules_repo(nfcore_dir)
    pipeline_dir = _create_minimal_pipeline(tmp_path, with_local_subworkflow=True)

    with (
        mock.patch("git.Remote.fetch", side_effect=git.GitCommandError("git fetch", 128)) as mock_fetch,
        mock.patch("rich.prompt.Confirm.ask", side_effect=AssertionError("Should not prompt to delete cache")),
        mock.patch("requests.get", side_effect=requests.exceptions.ConnectionError("offline")),
    ):
        sw_lint = nf_core.subworkflows.lint.SubworkflowLint(directory=pipeline_dir, local=True)
        sw_lint.lint(print_results=False, local=True)

    mock_fetch.assert_not_called()
    assert cache_dir.exists()
    assert len(sw_lint.failed) == 0
    passed_names = {r.lint_test for r in sw_lint.passed}
    assert "meta_yml_valid" in passed_names


@pytest.mark.parametrize("author_options", [["--author", "@testuser"], []], ids=["explicit", "prompt"])
def test_subworkflows_no_pull_create_offline(tmp_path, author_options):
    """`nf-core subworkflows --no-pull create` must succeed offline without calling git, gh, or Prettier."""
    pipeline_dir = _create_minimal_pipeline(tmp_path)
    git.Repo.init(pipeline_dir)
    runner = CliRunner()

    with (
        mock.patch("nf_core.utils.is_interactive", return_value=True),
        mock.patch("nf_core.components.create.run_prettier_on_file") as mock_prettier,
        mock.patch("nf_core.components.create.rich.prompt.Prompt.ask", return_value="@testuser") as mock_author,
        mock.patch("git.Repo.clone_from", side_effect=git.GitCommandError("git clone", 128)) as mock_clone,
        mock.patch("git.Remote.fetch", side_effect=git.GitCommandError("git fetch", 128)) as mock_fetch,
        mock.patch(
            "nf_core.components.create.subprocess.check_output",
            side_effect=subprocess.CalledProcessError(1, ["gh", "api", "/user"]),
        ) as mock_gh,
        mock.patch("requests.get", side_effect=requests.exceptions.ConnectionError("offline")),
    ):
        result = runner.invoke(
            nf_core.__main__.nf_core_cli,
            [
                "subworkflows",
                "--no-pull",
                "create",
                "mysubwf",
                "-d",
                str(pipeline_dir),
                *author_options,
            ],
        )

    assert result.exit_code == 0, f"CLI exited {result.exit_code}:\n{result.output}"
    mock_clone.assert_not_called()
    mock_fetch.assert_not_called()
    mock_gh.assert_not_called()
    mock_prettier.assert_not_called()
    assert mock_author.call_count == (0 if author_options else 1)
    assert (pipeline_dir / "subworkflows" / "local" / "mysubwf" / "main.nf").exists()
    assert (pipeline_dir / "subworkflows" / "local" / "mysubwf" / "meta.yml").exists()


def test_subworkflows_no_pull_lint_meta_yml_offline_no_cache_warns(tmp_path):
    """`nf-core subworkflows --no-pull lint --all -k meta_yml` offline without cache warns with 0 failures."""
    pipeline_dir = _create_minimal_pipeline(tmp_path, with_remote_subworkflow=True)
    runner = CliRunner()

    with (
        mock.patch("git.Repo.clone_from", side_effect=git.GitCommandError("git clone", 128)) as mock_clone,
        mock.patch("git.Remote.fetch", side_effect=git.GitCommandError("git fetch", 128)) as mock_fetch,
    ):
        result = runner.invoke(
            nf_core.__main__.nf_core_cli,
            [
                "subworkflows",
                "--no-pull",
                "lint",
                "-d",
                str(pipeline_dir),
                "--all",
                "-k",
                "meta_yml",
                "--plain-text",
            ],
        )

    assert result.exit_code == 0, f"CLI exited {result.exit_code}:\n{result.output}"
    mock_clone.assert_not_called()
    mock_fetch.assert_not_called()
    assert "Could not load meta.yml schema" in result.output


def test_update_meta_yml_fix_with_null_tools(tmp_path, offline_config):
    """`update_meta_yml_file` handles `tools: null` in meta.yml without raising TypeError."""
    _create_cached_modules_repo(offline_config)
    pipeline_dir = _create_minimal_pipeline(tmp_path, with_local_module=True)
    meta_yml = pipeline_dir / "modules" / "local" / "mytool" / "meta.yml"
    meta_yml.write_text("name: mytool\ntools:\nauthors: ['@testuser']\n", encoding="utf-8")

    with mock.patch("nf_core.modules.lint.run_prettier_on_file") as mock_prettier:
        module_lint = nf_core.modules.lint.ModuleLint(directory=pipeline_dir, fix=True, no_pull=True, local=True)
        mod = module_lint.all_local_components[0]
        module_lint._safe_parse_main_nf(mod)
        module_lint.update_meta_yml_file(mod)

    mock_prettier.assert_not_called()
    assert meta_yml.is_file()
    assert "name: mytool" in meta_yml.read_text(encoding="utf-8")


@pytest.mark.parametrize("payload", ["blocked", ["not", "an", "object"]], ids=["string", "list"])
def test_actions_schema_validation_non_object_json_proxy_response_warns(tmp_path, payload):
    """Corporate proxy returning valid non-object JSON warns cleanly instead of raising SchemaError."""
    pipeline_dir = _create_minimal_pipeline(tmp_path, with_workflow_yml=True)
    lint_obj = nf_core.pipelines.lint.PipelineLint(pipeline_dir)
    response = requests.Response()
    response.status_code = 200
    response._content = json.dumps(payload).encode("utf-8")

    with mock.patch("nf_core.pipelines.lint.actions_schema_validation.requests.get", return_value=response):
        results = lint_obj.actions_schema_validation()

    assert results["failed"] == []
    assert len(results["warned"]) == 1
    assert "schemastore.org" in results["warned"][0]


def test_all_remote_components_malformed_modules_json_raises_lookup_error(tmp_path):
    """Malformed modules.json entries keep raising LookupError in ComponentLint.all_remote_components."""
    pipeline_dir = _create_minimal_pipeline(tmp_path)

    with (
        mock.patch(
            "nf_core.modules.modules_json.ModulesJson.get_all_components",
            return_value={"https://github.com/nf-core/modules.git": "malformed"},
        ),
        pytest.raises(LookupError, match="Error parsing modules.json"),
    ):
        nf_core.modules.lint.ModuleLint(directory=pipeline_dir, no_pull=True)
