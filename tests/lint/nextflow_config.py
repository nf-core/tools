import nf_core.create
import nf_core.lint
import subprocess
from unittest import mock

def test_nextflow_config_example_pass(self):
    """Tests that config variable existence test works with good pipeline example"""
    self.lint_obj._load_pipeline_config()
    result = self.lint_obj.nextflow_config()
    assert len(result["failed"]) == 0
    assert len(result["warned"]) == 0


def test_nextflow_config_bad_name_fail(self):
    """Tests that config variable existence test fails with bad pipeline name"""
    new_pipeline = self._make_pipeline_copy()
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load_pipeline_config()

    lint_obj.nf_config["manifest.name"] = "bad_name"
    result = lint_obj.nextflow_config()
    assert len(result["failed"]) > 0
    assert len(result["warned"]) == 0


def test_nextflow_config_dev_in_release_mode_failed(self):
    """Tests that config variable existence test fails with dev version in release mode"""
    new_pipeline = self._make_pipeline_copy()
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load_pipeline_config()

    lint_obj.release_mode = True
    lint_obj.nf_config["manifest.version"] = "dev_is_bad_name"
    result = lint_obj.nextflow_config()
    assert len(result["failed"]) > 0
    assert len(result["warned"]) == 0

@mock.patch("subprocess.run")
def test_nextflow_config_missing_test_profile_failed(self, mock_subprocess):
    """Tests that the test fails if nextflow command with `-profile test` exits
    with exit code 1."""
    self.lint_obj._load_pipeline_config()
    with mock.patch("subprocess.run") as mock_subprocess:
        mock_subprocess.return_value = mock.Mock(returncode=1)
        result = self.lint_obj.nextflow_config()
        mock_subprocess.assert_called_once_with(
            ["nextflow", "config", "-flat", "-profile", "test"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    assert len(result["failed"]) > 0
    assert len(result["warned"]) == 0
