"""CodSpeed wall-time benchmarks for module linting and git history lookups (offline)."""

import shutil
import sys

import pytest

# Installed in addition to the template's fastqc and multiqc
EXTRA_MODULES = ["samtools/sort", "fastp"]

OUTDATED_COMMIT_DEPTH = 10

# Stub out the network calls made during module linting
_OFFLINE_LINT_SETUP = """
from unittest import mock

import requests

import nf_core.utils
from nf_core.modules.modules_repo import ModulesRepo


def _fake_anaconda_package(dep, dep_channels=None):
    version = dep.split("=")[1] if "=" in dep else "0"
    return {"versions": [version], "latest_version": version}


nf_core.utils.anaconda_package = _fake_anaconda_package
nf_core.utils.fetch_wf_config = lambda *args, **kwargs: {}
requests.head = lambda *args, **kwargs: mock.Mock(ok=True, status_code=200)
ModulesRepo.no_pull_global = True
"""


@pytest.fixture(scope="session")
def pipeline_with_modules(generated_pipeline, modules_cache, tmp_path_factory):
    """Copy of the generated pipeline with EXTRA_MODULES installed."""
    from nf_core.modules.install import ModuleInstall

    pipeline_dir = tmp_path_factory.mktemp("pipeline_with_modules") / "pipeline"
    shutil.copytree(generated_pipeline, pipeline_dir)
    installer = ModuleInstall(pipeline_dir, prompt=False, force=True)
    for module in EXTRA_MODULES:
        assert installer.install(module), f"Could not install {module}"
    return pipeline_dir


def test_modules_lint_all(benchmark_command, pipeline_with_modules):
    """Lint all modules in a pipeline. Uses the API, as the CLI exits non-zero on lint failures."""
    script = f"""{_OFFLINE_LINT_SETUP}
from nf_core.modules.lint import ModuleLint

ModuleLint({str(pipeline_with_modules)!r}, hide_progress=True).lint(all_modules=True, print_results=False)
"""
    benchmark_command([sys.executable, "-c", script], rounds=3, warmup_rounds=1)


@pytest.fixture(scope="session")
def outdated_fastqc(modules_cache, tmp_path_factory):
    """fastqc installed from an older commit."""
    modules_repo = modules_cache
    commits = list(modules_repo.get_component_git_log("fastqc", "modules", depth=OUTDATED_COMMIT_DEPTH + 1))
    sha = commits[min(OUTDATED_COMMIT_DEPTH, len(commits) - 1)]["git_sha"]
    install_dir = tmp_path_factory.mktemp("outdated_fastqc")
    assert modules_repo.install_component("fastqc", install_dir, sha, "modules")
    return modules_repo, install_dir / "fastqc"


def test_find_correct_commit_sha(benchmark, outdated_fastqc, tmp_path):
    """Find the commit matching an installed module, as done when repairing modules.json."""
    from nf_core.modules.modules_json import ModulesJson

    modules_repo, fastqc_dir = outdated_fastqc
    modules_json = ModulesJson(tmp_path, no_prompts=True)

    def find_sha():
        assert modules_json.find_correct_commit_sha("modules", "fastqc", fastqc_dir, modules_repo) is not None

    benchmark.pedantic(find_sha, rounds=3, warmup_rounds=1)
