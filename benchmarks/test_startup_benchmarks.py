"""CodSpeed wall-time benchmarks for nf-core CLI start-up cost.

Each round starts a fresh `nf-core` process, so lazily-imported dependencies
(pydantic, requests, questionary, PyGithub, trogon, ...) are paid for every
time, just like for a user. Run them under CodSpeed's "walltime" instrument:
the "simulation" instrument only profiles the parent test process and never
sees the child process.
"""

import pytest

COMMAND_GROUPS = ["pipelines", "modules", "subworkflows", "test-datasets"]


def test_cli_help_startup(benchmark_cli):
    """`nf-core --help`"""
    benchmark_cli("--help", rounds=10, warmup_rounds=2)


@pytest.mark.parametrize("command_group", COMMAND_GROUPS)
def test_cli_command_group_help_startup(benchmark_cli, command_group):
    """`nf-core <group> --help`"""
    benchmark_cli(command_group, "--help", rounds=10, warmup_rounds=2)
