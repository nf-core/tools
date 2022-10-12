#!/usr/bin/env python
""" Tests covering the command-line code.
"""

import tempfile
import unittest
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


class TestCli(unittest.TestCase):
    """Class for testing the commandline interface"""

    def setUp(self):
        self.runner = CliRunner()

    def assemble_params(self, params):
        """Assemble a dictionnary of parameters into a list of arguments for the cli

        Note:
            if the value of a parameter is None, it will be considered a flag

        Args:
            params (dict): dict of parameters to assemble"""
        arg_list = [[f"--{key}"] + ([value] if value is not None else []) for key, value in params.items()]
        return [item for arg in arg_list for item in arg]

    def invoke_cli(self, cmd):
        """Invoke the commandline interface using a list of parameters

        Args:
            cmd (list): commandline to execute
        """
        return self.runner.invoke(nf_core.__main__.nf_core_cli, cmd)

    def test_cli_help(self):
        """Test the main launch function with --help"""
        result = self.invoke_cli(["--help"])
        assert result.exit_code == 0
        assert "Show the version and exit." in result.output

    def test_cli_bad_subcommand(self):
        """Test the main launch function with verbose flag and an unrecognised argument"""
        result = self.invoke_cli(["-v", "foo"])
        assert result.exit_code == 2
        # Checks that -v was considered valid
        assert "No such command" in result.output

    @mock.patch("nf_core.list.list_workflows", return_value="pipeline test list")
    def test_cli_list(self, mock_list_workflows):
        """Test nf-core pipelines are listed and cli parameters are passed on."""
        params = {
            "sort": "name",
            "json": None,
            "show-archived": None,
        }
        cmd = ["list"] + self.assemble_params(params) + ["kw1", "kw2"]
        result = self.invoke_cli(cmd)

        mock_list_workflows.assert_called_once_with(
            tuple(cmd[-2:]), params["sort"], "json" in params, "show-archived" in params
        )
        assert "pipeline test list" in result.output
