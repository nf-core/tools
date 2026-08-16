"""Tests for the Apple Container fetcher in nf-core download."""

import os
import shutil
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest import mock

import pytest

from nf_core.pipelines.download.apple_container import AppleContainerFetcher

from ...utils import with_temporary_folder


class AppleContainerTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def use_caplog(self, caplog):
        self._caplog = caplog

    #
    # Test for AppleContainerFetcher initialization and output directory
    #
    @pytest.mark.skipif(
        shutil.which("container") is None,
        reason="Can't test Apple Container fetcher without Apple Container CLI installed.",
    )
    @with_temporary_folder
    def test_apple_container_output_dir(self, tmp_path):
        tmp_path = Path(tmp_path)
        fetcher = AppleContainerFetcher(
            outdir=tmp_path,
            container_library=[],
            registry_set=[],
        )
        assert fetcher.get_container_output_dir() == tmp_path / "apple-container-images"

    #
    # Test for AppleContainerFetcher._write_apple_container_load_message
    #
    @pytest.mark.skipif(
        shutil.which("container") is None,
        reason="Can't test Apple Container fetcher without Apple Container CLI installed.",
    )
    @with_temporary_folder
    def test_apple_container_write_load_message(self, tmp_path):
        tmp_path = Path(tmp_path)
        fetcher = AppleContainerFetcher(
            outdir=tmp_path,
            container_library=[],
            registry_set=[],
        )
        img_dir = fetcher.get_container_output_dir()
        img_dir.mkdir()
        with redirect_stderr(StringIO()) as f:
            fetcher._write_apple_container_load_message()

        output = f.getvalue()
        # Check that the message references correct scripts
        # Rich may insert hard line breaks in long paths, so strip all whitespace for path check
        assert "apple-container-images" in output.replace("\n", "").replace(" ", "")
        assert "appleContainer-load.sh" in output

        # Check that the script was written and is executable
        assert (img_dir / "appleContainer-load.sh").exists()
        assert os.access(img_dir / "appleContainer-load.sh", os.X_OK)

    #
    # Test that cleanup calls the Apple Container message, not the Docker one
    #
    @pytest.mark.skipif(
        shutil.which("container") is None,
        reason="Can't test Apple Container fetcher without Apple Container CLI installed.",
    )
    @with_temporary_folder
    def test_apple_container_cleanup(self, tmp_path):
        tmp_path = Path(tmp_path)
        fetcher = AppleContainerFetcher(
            outdir=tmp_path,
            container_library=[],
            registry_set=[],
        )
        img_dir = fetcher.get_container_output_dir()
        img_dir.mkdir()
        with redirect_stderr(StringIO()) as f:
            fetcher.cleanup()

        output = f.getvalue()
        # Should mention Apple Container, not Docker/podman
        assert "appleContainer-load.sh" in output
        # Should NOT have the Docker-specific "podman-load.sh (experimental)" wording
        assert "experimental" not in output
        assert "podman" not in output

    #
    # Test that gather_registries includes appleContainer.registry key
    #
    @pytest.mark.skipif(
        shutil.which("container") is None,
        reason="Can't test Apple Container fetcher without Apple Container CLI installed.",
    )
    @with_temporary_folder
    @mock.patch("nf_core.pipelines.download.container_fetcher.ContainerFetcher.gather_config_registries")
    def test_apple_container_gather_registries(self, tmp_path, mock_gather_config):
        tmp_path = Path(tmp_path)
        mock_gather_config.return_value = {"quay.io"}
        fetcher = AppleContainerFetcher(
            outdir=tmp_path,
            container_library=[],
            registry_set=["docker.io"],
        )
        registries = fetcher.gather_registries(tmp_path)
        # Should have called gather_config_registries with the apple container key
        mock_gather_config.assert_called_once_with(
            tmp_path,
            ["appleContainer.registry", "docker.registry", "podman.registry"],
        )
        assert "quay.io" in registries
        assert "docker.io" in registries

    #
    # Test that check_and_set_implementation finds the container binary
    #
    @pytest.mark.skipif(
        shutil.which("container") is None,
        reason="Can't test Apple Container fetcher without Apple Container CLI installed.",
    )
    @with_temporary_folder
    def test_apple_container_check_implementation(self, tmp_path):
        tmp_path = Path(tmp_path)
        fetcher = AppleContainerFetcher(
            outdir=tmp_path,
            container_library=[],
            registry_set=[],
        )
        assert fetcher.implementation == "container"

    #
    # Test that check_and_set_implementation raises when container CLI is missing
    #
    @with_temporary_folder
    @mock.patch("shutil.which", return_value=None)
    def test_apple_container_missing_cli_raises(self, tmp_path, mock_which):
        tmp_path = Path(tmp_path)
        with pytest.raises(OSError, match="Apple Container CLI"):
            AppleContainerFetcher(
                outdir=tmp_path,
                container_library=[],
                registry_set=[],
            )

    #
    # Test that construct_pull_command produces the correct command
    #
    @pytest.mark.skipif(
        shutil.which("container") is None,
        reason="Can't test Apple Container fetcher without Apple Container CLI installed.",
    )
    @with_temporary_folder
    def test_apple_container_pull_command(self, tmp_path):
        tmp_path = Path(tmp_path)
        fetcher = AppleContainerFetcher(
            outdir=tmp_path,
            container_library=[],
            registry_set=[],
        )
        cmd = fetcher.construct_pull_command("quay.io/biocontainers/fastqc:0.12.1")
        assert cmd == ["container", "image", "pull", "--platform", "linux/arm64", "quay.io/biocontainers/fastqc:0.12.1"]

    #
    # Test that construct_save_command produces the correct command
    #
    @pytest.mark.skipif(
        shutil.which("container") is None,
        reason="Can't test Apple Container fetcher without Apple Container CLI installed.",
    )
    @with_temporary_folder
    def test_apple_container_save_command(self, tmp_path):
        tmp_path = Path(tmp_path)
        fetcher = AppleContainerFetcher(
            outdir=tmp_path,
            container_library=[],
            registry_set=[],
        )
        output_path = tmp_path / "image.tar"
        cmd = fetcher.construct_save_command(output_path, "quay.io/biocontainers/fastqc:0.12.1")
        assert cmd == [
            "container",
            "image",
            "save",
            "--platform",
            "linux/arm64",
            "--output",
            str(output_path),
            "quay.io/biocontainers/fastqc:0.12.1",
        ]
