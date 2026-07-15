"""CodSpeed wall-time benchmarks for nf-core CLI start-up cost.

These spawn a fresh interpreter per round so that heavy, lazily-imported
dependencies (pydantic, requests, questionary, PyGithub, trogon, ...) are not
cached in sys.modules from a previous round. Run them under CodSpeed's
"walltime" instrument: the "simulation" instrument only profiles the parent
test process and never sees the child interpreter's import cost.

Rounds are kept low because each one pays for a full interpreter boot.
"""

import os
import shutil
import subprocess
import sys

import pytest

IMPORT_CMD = [sys.executable, "-c", "import nf_core.__main__"]
HELP_CMD = [sys.executable, "-m", "nf_core", "--help"]
COMMAND_GROUPS = ["pipelines", "modules", "subworkflows", "test-datasets"]

# Keep the help invocation offline and deterministic.
_ENV = {**os.environ, "NFCORE_NO_VERSION_CHECK": "1"}


def _benchmark_command(benchmark, command):
    def run():
        subprocess.run(command, check=True, capture_output=True, env=_ENV)

    benchmark.pedantic(run, rounds=10, warmup_rounds=2)


def _cli_script(setup, args):
    return f"{setup}\nimport sys\nsys.argv = {args!r}\nfrom nf_core.__main__ import run_nf_core\nrun_nf_core()"


@pytest.fixture(scope="session")
def generated_pipeline(tmp_path_factory):
    """Render a real pipeline scaffold once, reused by the realistic benchmarks.

    Generation is expensive and identical for every consumer, so it happens a
    single time per session and outside any measured rounds. Consumers that
    mutate the pipeline (e.g. installing a module) must work on a copy so the
    shared scaffold stays pristine and the suite is order-independent.
    """
    from nf_core.pipelines.create.create import PipelineCreate

    pipeline_dir = tmp_path_factory.mktemp("pipeline_fixture") / "pipeline"
    PipelineCreate("benchmark", "benchmark pipeline", "nf-core", outdir=pipeline_dir, no_git=True).init_pipeline()
    return pipeline_dir


@pytest.fixture(scope="session")
def modules_cache():
    """Ensure a local nf-core/modules clone exists, without ever fetching.

    Constructing ``ModulesRepo`` clones the remote into ``NFCORE_DIR`` only if it
    is not already present; ``no_pull_global`` suppresses the ``git fetch`` on an
    existing clone. In CI the clone is warmed by an earlier, network-enabled
    workflow step, so this fixture (and every measured round) runs offline. When
    run locally against a cold cache it performs the one-off clone here, outside
    the measured rounds.
    """
    from nf_core.modules.modules_repo import ModulesRepo

    ModulesRepo.no_pull_global = True
    ModulesRepo()


def test_import_main_startup(benchmark):
    """Wall-time cost of importing the CLI entry point in a fresh interpreter."""
    _benchmark_command(benchmark, IMPORT_CMD)


def test_cli_help_startup(benchmark):
    """Wall-time cost of a full `nf-core --help` invocation."""
    _benchmark_command(benchmark, HELP_CMD)


@pytest.mark.parametrize("command_group", COMMAND_GROUPS)
def test_cli_command_group_help_startup(benchmark, command_group):
    """Wall-time cost of loading each top-level command tree and rendering its help."""
    _benchmark_command(benchmark, [sys.executable, "-m", "nf_core", command_group, "--help"])


def test_pipelines_create_startup(benchmark, tmp_path):
    """Start the create command, stubbing only template generation and other writes."""
    args = [
        "nf-core",
        "pipelines",
        "create",
        "--name",
        "benchmark",
        "--description",
        "benchmark pipeline",
        "--author",
        "nf-core",
        "--outdir",
        str(tmp_path / "pipeline"),
    ]
    setup = (
        "from nf_core.pipelines.create.create import PipelineCreate\nPipelineCreate.init_pipeline = lambda self: None"
    )
    _benchmark_command(benchmark, [sys.executable, "-c", _cli_script(setup, args)])


def test_modules_install_startup(benchmark, generated_pipeline, modules_cache, tmp_path):
    """Install a real module into a real pipeline, offline.

    The pipeline scaffold (``generated_pipeline``) and the nf-core/modules clone
    (``modules_cache``) are both prepared once, outside the measured rounds. The
    rounds then run the real install (git checkout + file copy + modules.json
    write) against a private copy of the scaffold. ``no_pull_global`` suppresses
    the per-round ``git fetch`` and ``--force`` avoids the re-install prompt, so
    every round is deterministic and network-free.
    """
    target = tmp_path / "pipeline"
    shutil.copytree(generated_pipeline, target)
    args = ["nf-core", "modules", "install", "fastp", "-d", str(target), "--force"]
    setup = "from nf_core.modules.modules_repo import ModulesRepo\nModulesRepo.no_pull_global = True"
    _benchmark_command(benchmark, [sys.executable, "-c", _cli_script(setup, args)])


def test_pipelines_schema_lint_startup(benchmark, generated_pipeline):
    """Lint a real, freshly generated pipeline schema.

    The schema fixture is rendered once by ``generated_pipeline`` (outside the
    measured rounds); the benchmark then runs the real lint (JSON parse +
    JSON-Schema validation + default-param checks). Only ``fetch_wf_config`` is
    stubbed to skip the ``nextflow config`` JVM subprocess, which would
    otherwise dominate wall time and require Nextflow on the runner.
    """
    args = ["nf-core", "pipelines", "schema", "lint", str(generated_pipeline)]
    setup = "import nf_core.utils\nnf_core.utils.fetch_wf_config = lambda *args, **kwargs: {}"
    _benchmark_command(benchmark, [sys.executable, "-c", _cli_script(setup, args)])
