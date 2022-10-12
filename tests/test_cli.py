#!/usr/bin/env python
""" Tests covering the command-line code.
"""

from unittest import mock

from click.testing import CliRunner

import nf_core.__main__


@mock.patch("nf_core.__main__.nf_core_cli")
def test_header(mock_cli):
    """Just try to execute the header function"""
    nf_core.__main__.run_nf_core()


@mock.patch("nf_core.__main__.nf_core_cli")
@mock.patch("nf_core.utils.check_if_outdated", return_value=(True, None, "dummy_version"))
def test_header_outdated(mock_check_outdated, mock_nf_core_cli, capsys):
    """Check cli notifies the user when nf_core is outdated"""
    nf_core.__main__.run_nf_core()
    captured = capsys.readouterr()
    assert "There is a new version of nf-core/tools available! (dummy_version)" in captured.err


def test_cli_help():
    """Test the main launch function with --help"""
    runner = CliRunner()
    result = runner.invoke(nf_core.__main__.nf_core_cli, ["--help"])
    assert result.exit_code == 0
    assert "Show the version and exit." in result.output


def test_cli_bad_subcommand():
    """Test the main launch function with verbose flag and an unrecognised argument"""
    runner = CliRunner()
    result = runner.invoke(nf_core.__main__.nf_core_cli, ["-v", "foo"])
    assert result.exit_code == 2
    # Checks that -v was considered valid
    assert "No such command" in result.output
