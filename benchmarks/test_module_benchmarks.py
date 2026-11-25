"""CodSpeed wall-time benchmarks for `nf-core modules` commands."""

import shutil

import pytest

# The nf-core/modules clone is prepared once by ``modules_cache``, so no round measures a `git fetch`
MODULES = ("modules", "--no-pull")

# Installed in addition to the modules that come with the template
EXTRA_MODULES = ["samtools/sort", "fastp"]

# How many fastqc commits behind the latest one the outdated install is
OUTDATED_COMMIT_DEPTH = 10

pytestmark = pytest.mark.usefixtures("modules_cache")


def _pipeline_with(generated_pipeline, tmp_path_factory, name, modules, sha=None):
    """Copy of the generated pipeline with ``modules`` installed (at ``sha``, if given)."""
    from nf_core.modules.install import ModuleInstall

    pipeline_dir = tmp_path_factory.mktemp(name) / "pipeline"
    shutil.copytree(generated_pipeline, pipeline_dir, symlinks=True)
    installer = ModuleInstall(pipeline_dir, prompt=False, force=True, sha=sha)
    for module in modules:
        assert installer.install(module), f"Could not install {module}"
    return pipeline_dir


@pytest.fixture(scope="session")
def pipeline_with_modules(generated_pipeline, tmp_path_factory):
    return _pipeline_with(generated_pipeline, tmp_path_factory, "pipeline_with_modules", EXTRA_MODULES)


@pytest.fixture(scope="session")
def pipeline_with_outdated_fastqc(generated_pipeline, modules_cache, tmp_path_factory):
    commits = list(modules_cache.get_component_git_log("fastqc", "modules", depth=OUTDATED_COMMIT_DEPTH + 1))
    sha = commits[OUTDATED_COMMIT_DEPTH]["git_sha"]
    return _pipeline_with(generated_pipeline, tmp_path_factory, "pipeline_outdated_fastqc", ["fastqc"], sha=sha)


def test_modules_list_local(benchmark_cli, pipeline_with_modules):
    """`nf-core modules list local` in a pipeline."""
    benchmark_cli(*MODULES, "list", "local", "--dir", pipeline_with_modules)


def test_modules_install(benchmark_cli, generated_pipeline, tmp_path):
    """`nf-core modules install` of a module that isn't in the pipeline yet."""
    target = tmp_path / "pipeline"
    benchmark_cli(*MODULES, "install", "fastp", "--dir", target, reset=(generated_pipeline, target))


def test_modules_update(benchmark_cli, pipeline_with_outdated_fastqc, tmp_path):
    """`nf-core modules update` of a module that is several commits behind."""
    target = tmp_path / "pipeline"
    benchmark_cli(
        *MODULES,
        "update",
        "fastqc",
        "--dir",
        target,
        "--no-preview",
        rounds=3,
        reset=(pipeline_with_outdated_fastqc, target),
    )


def test_modules_lint_all(benchmark_cli, pipeline_with_modules):
    """`nf-core modules lint --all` in a pipeline.

    Template modules can fail lint tests newer than they are, so only require the summary.
    """
    benchmark_cli(
        *MODULES,
        "lint",
        "--all",
        "--dir",
        pipeline_with_modules,
        rounds=2,
        expect_output="LINT RESULTS SUMMARY",
    )
