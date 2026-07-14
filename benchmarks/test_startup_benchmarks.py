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

IMPORT_CMD = [sys.executable, "-c", "import nf_core.__main__"]
HELP_CMD = [sys.executable, "-m", "nf_core", "--help"]

# Keep the help invocation offline and deterministic.
_ENV = {**os.environ, "NFCORE_NO_VERSION_CHECK": "1"}


def test_import_main_startup(benchmark):
    """Wall-time cost of importing the CLI entry point in a fresh interpreter."""

    def run():
        subprocess.run(IMPORT_CMD, check=True, capture_output=True)

    benchmark.pedantic(run, rounds=10, warmup_rounds=2)


def test_cli_help_startup(benchmark):
    """Wall-time cost of a full `nf-core --help` invocation."""

    def run():
        subprocess.run(HELP_CMD, check=True, capture_output=True, env=_ENV)

    benchmark.pedantic(run, rounds=10, warmup_rounds=2)
