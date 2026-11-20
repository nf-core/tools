"""Shared fixtures for the CodSpeed benchmarks."""

import os
import subprocess

import pytest

_ENV = {**os.environ, "NFCORE_NO_VERSION_CHECK": "1", "HIDE_PROGRESS": "1"}


@pytest.fixture
def benchmark_command(benchmark):
    """Benchmark running a command in a subprocess."""

    def run_benchmark(command, rounds=10, warmup_rounds=2):
        def run():
            subprocess.run(command, check=True, capture_output=True, env=_ENV)

        benchmark.pedantic(run, rounds=rounds, warmup_rounds=warmup_rounds)

    return run_benchmark


@pytest.fixture(scope="session")
def generated_pipeline(tmp_path_factory):
    """Create a pipeline once per session. Copy it before modifying it."""
    from nf_core.pipelines.create.create import PipelineCreate

    pipeline_dir = tmp_path_factory.mktemp("pipeline_fixture") / "pipeline"
    PipelineCreate("benchmark", "benchmark pipeline", "nf-core", outdir=pipeline_dir, no_git=True).init_pipeline()
    return pipeline_dir


@pytest.fixture(scope="session")
def modules_cache():
    """Return the local nf-core/modules clone, cloning it if missing but never pulling."""
    from nf_core.modules.modules_repo import ModulesRepo

    ModulesRepo.no_pull_global = True
    return ModulesRepo()
