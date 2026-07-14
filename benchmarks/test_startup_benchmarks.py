"""CodSpeed wall-time benchmarks for nf-core CLI start-up cost.

These spawn a fresh interpreter per round so that heavy, lazily-imported
dependencies (pydantic, requests, questionary, PyGithub, trogon, ...) are not
cached in sys.modules from a previous round. Run them under CodSpeed's
"walltime" instrument: the "simulation" instrument only profiles the parent
test process and never sees the child interpreter's import cost.

Rounds are kept low because each one pays for a full interpreter boot.
"""

import os
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


def test_modules_install_startup(benchmark, tmp_path):
    """Start module installation, stubbing only the remote clone and resulting writes."""
    args = ["nf-core", "modules", "install", "fastp", "-d", str(tmp_path)]
    setup = """import nf_core.modules.install as install_module
install_module.ModuleInstall = type(
    "ModuleInstall",
    (),
    {
        "__init__": lambda self, *args, **kwargs: None,
        "install": lambda self, *args, **kwargs: True,
    },
)"""
    _benchmark_command(benchmark, [sys.executable, "-c", _cli_script(setup, args)])
