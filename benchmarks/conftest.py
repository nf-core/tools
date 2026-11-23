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
    every round, for commands that modify the pipeline. ``clean=path`` deletes
    ``path`` before every round, for commands that must start from scratch.
    ``expect_output`` is for the linters, which exit 1 on findings: exit code 1 is
    then accepted only if the output contains it, so a crash can't pass as a speedup.
    """

    def run_benchmark(*args, rounds=5, warmup_rounds=1, reset=None, clean=None, expect_output=None):
        command = [NF_CORE, *map(str, args)]

        def target():
            result = subprocess.run(command, capture_output=True, text=True, env=_ENV)
            output = result.stdout + result.stderr
            ok_codes = (0,) if expect_output is None else (0, 1)
            assert result.returncode in ok_codes, f"exit code {result.returncode}:\n{output}"
            assert expect_output is None or expect_output in output, f"{expect_output!r} not in output:\n{output}"

        def setup():
            if clean:
                shutil.rmtree(clean, ignore_errors=True)
            if reset:
                source, dest = reset
                shutil.rmtree(dest, ignore_errors=True)
                shutil.copytree(source, dest, symlinks=True)

        benchmark.pedantic(target, setup=setup if reset or clean else None, rounds=rounds, warmup_rounds=warmup_rounds)

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
