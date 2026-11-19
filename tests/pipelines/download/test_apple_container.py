"""Tests for the Apple Container fetcher in nf-core download."""

import os
import shutil
import subprocess
import tarfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest import mock

import pytest

from nf_core.pipelines.download.apple_container import AppleContainerFetcher
from nf_core.pipelines.download.docker import DockerError

from ...utils import with_temporary_folder


def _apple_container_running() -> bool:
    """True if the `container` CLI is installed and its system services are started."""
    container_binary = shutil.which("container")
    if container_binary is None:
        return False
    return subprocess.run([container_binary, "system", "status"], capture_output=True, check=False).returncode == 0


requires_apple_container = pytest.mark.skipif(
    not _apple_container_running(),
    reason="Can't test what Apple Container does if it's not installed and running.",
)


class AppleContainerTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def use_caplog(self, caplog):
        self._caplog = caplog

    def setUp(self):
        # Don't depend on the Apple Container system services being started on the test host
        patcher = mock.patch("nf_core.utils.run_cmd", return_value=(b"", b""))
        self.mock_run_cmd = patcher.start()
        self.addCleanup(patcher.stop)

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
        assert fetcher.implementation == "apple container"
        self.mock_run_cmd.assert_called_once_with(shutil.which("container"), "system status")

    #
    # Test that check_and_set_implementation raises when the system services are not running
    #
    @with_temporary_folder
    @mock.patch("shutil.which", return_value="/usr/local/bin/container")
    def test_apple_container_services_not_running_raises(self, tmp_path, mock_which):
        self.mock_run_cmd.side_effect = RuntimeError("apiserver is not running")
        with pytest.raises(OSError, match="container system start"):
            AppleContainerFetcher(
                outdir=Path(tmp_path),
                container_library=[],
                registry_set=[],
            )
        self.mock_run_cmd.assert_called_once_with("/usr/local/bin/container", "system status")

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
        assert cmd == ["container", "image", "pull", "--platform", "linux/amd64", "quay.io/biocontainers/fastqc:0.12.1"]

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
            "linux/amd64",
            "--output",
            str(output_path),
            "quay.io/biocontainers/fastqc:0.12.1",
        ]

    #
    # Integration tests: these run the real `container` CLI against public registries
    #
    def _make_fetcher(self, tmp_path: Path) -> AppleContainerFetcher:
        fetcher = AppleContainerFetcher(
            outdir=tmp_path,
            container_library=[],
            registry_set=[],
        )
        fetcher.progress = mock.MagicMock()
        return fetcher

    #
    # Tests for 'pull_image'
    #
    @requires_apple_container
    @with_temporary_folder
    def test_apple_container_pull_image(self, tmp_path):
        fetcher = self._make_fetcher(Path(tmp_path))
        task = mock.MagicMock()

        # Successful pulls: short name and absolute URI
        fetcher.pull_image("hello-world", task)
        fetcher.pull_image("docker.io/bschiffthaler/sed", task)

        # Known `container` CLI limitation (v1.2.2): Seqera Containers serve a bare single-platform
        # OCI manifest, which Apple Container rejects with "does not list any supported platform".
        # If this starts passing, upstream has fixed it and this can move to the successful pulls.
        with pytest.raises(DockerError.OtherError):
            fetcher.pull_image("community.wave.seqera.io/library/umi-transfer:1.0.0--e5b0c1a65b8173b6", task)

        # Failed pulls must raise, not pass silently
        with pytest.raises((DockerError.ImageNotFoundError, DockerError.OtherError)):
            fetcher.pull_image("docker.io/bschiffthaler/nothingtopullhere", task)
        with pytest.raises((DockerError.InvalidTagError, DockerError.OtherError)):
            fetcher.pull_image("ghcr.io/ewels/multiqc:go-rewrite", task)
        with pytest.raises(DockerError.OtherError):
            fetcher.pull_image("Not:A:Valid//reference", task)

    #
    # Tests for 'save_image'
    #
    @requires_apple_container
    @with_temporary_folder
    def test_apple_container_save_image_not_pulled(self, tmp_path):
        tmp_path = Path(tmp_path)
        fetcher = self._make_fetcher(tmp_path)
        output_path = tmp_path / "not-pulled.tar"
        with pytest.raises(DockerError.ImageNotPulledError):
            fetcher.save_image(
                "this-image-cannot-possibly-be-pulled-to-this-machine:latest",
                output_path,
                mock.MagicMock(),
            )
        assert not output_path.exists()

    #
    # Tests for 'pull_and_save_image'
    #
    @requires_apple_container
    @with_temporary_folder
    def test_apple_container_pull_and_save_image(self, tmp_path):
        tmp_path = Path(tmp_path)
        fetcher = self._make_fetcher(tmp_path)
        output_path = tmp_path / "hello-world.tar"

        progress = fetcher.progress = mock.MagicMock()

        fetcher.pull_and_save_image("hello-world", output_path)

        assert output_path.exists()
        assert tarfile.is_tarfile(output_path)
        assert "ERROR" not in [record.levelname for record in self._caplog.records]
        progress.advance_remote_fetch_task.assert_called_once()

    @requires_apple_container
    @with_temporary_folder
    def test_apple_container_pull_and_save_image_missing(self, tmp_path):
        tmp_path = Path(tmp_path)
        fetcher = self._make_fetcher(tmp_path)
        output_path = tmp_path / "nothingtopullhere.tar"

        progress = fetcher.progress = mock.MagicMock()

        # Errors are logged, not raised, so that one bad image doesn't stop the whole download
        fetcher.pull_and_save_image("docker.io/bschiffthaler/nothingtopullhere", output_path)

        assert not output_path.exists()
        assert "ERROR" in [record.levelname for record in self._caplog.records]
        progress.advance_remote_fetch_task.assert_called_once()

    #
    # Tests for 'fetch_containers': end-to-end through the base class and fetch_remote_containers
    #
    @requires_apple_container
    @with_temporary_folder
    @mock.patch.object(AppleContainerFetcher, "gather_registries", return_value=set())
    def test_apple_container_fetch_containers(self, tmp_path, mock_gather_registries):
        tmp_path = Path(tmp_path)
        fetcher = AppleContainerFetcher(
            outdir=tmp_path,
            container_library=[],
            registry_set=[],
            hide_progress=True,
        )
        out_dir = fetcher.get_container_output_dir()
        out_dir.mkdir()

        good = "hello-world"
        bad = "docker.io/bschiffthaler/nothingtopullhere"
        fetcher.fetch_containers([good, bad], [], workflow_directory=tmp_path)

        good_tar = out_dir / fetcher.get_container_filename(good)
        assert good_tar.exists()
        assert tarfile.is_tarfile(good_tar)
        assert not (out_dir / fetcher.get_container_filename(bad)).exists()
