"""Shared fixtures for the CodSpeed benchmarks.

Every benchmark measures a real ``nf-core`` CLI command in a fresh subprocess,
the same way a user would type it, so the measured time is what the user waits
for. Nothing inside nf-core is stubbed during the measured rounds. Expensive
preparation (creating a pipeline, cloning nf-core/modules, ...) happens in
fixtures through the Python API, outside the measured rounds.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# The console script installed next to the interpreter, i.e. what users run as `nf-core`
NF_CORE = str(Path(sys.executable).with_name("nf-core"))

# The daily "new version available" check is the only thing we turn off:
# it is cached per day, so it would only add network noise to a single round.
_ENV = {**os.environ, "NFCORE_NO_VERSION_CHECK": "1"}


@pytest.fixture
def benchmark_cli(benchmark):
    """Benchmark a single `nf-core <args>` invocation.

    ``reset=(source, target)`` replaces ``target`` with a copy of ``source`` before
    every round, for commands that modify the pipeline. Set ``check=False`` for
    commands that exit non-zero on findings (the linters).
    """

    def run_benchmark(*args, rounds=5, warmup_rounds=1, reset=None, check=True):
        command = [NF_CORE, *map(str, args)]

        def target():
            subprocess.run(command, check=check, capture_output=True, env=_ENV)

        def setup():
            source, dest = reset
            shutil.rmtree(dest, ignore_errors=True)
            shutil.copytree(source, dest, symlinks=True)

        benchmark.pedantic(target, setup=setup if reset else None, rounds=rounds, warmup_rounds=warmup_rounds)

    return run_benchmark


@pytest.fixture(scope="session")
def generated_pipeline(tmp_path_factory):
    """Create a pipeline once per session. Copy it before modifying it."""
    from nf_core.pipelines.create.create import PipelineCreate

    pipeline_dir = tmp_path_factory.mktemp("pipeline_fixture") / "pipeline"
    PipelineCreate("benchmark", "benchmark pipeline", "nf-core", outdir=pipeline_dir).init_pipeline()
    return pipeline_dir


@pytest.fixture(scope="session")
def modules_cache():
    """Return a ModulesRepo for the local nf-core/modules clone, cloning it if missing.

    ``no_pull_global`` only stops the fixtures in this process from fetching; the
    benchmarked commands get ``--no-pull`` on their command line instead.
    """
    from nf_core.modules.modules_repo import ModulesRepo

    ModulesRepo.no_pull_global = True
    return ModulesRepo()
