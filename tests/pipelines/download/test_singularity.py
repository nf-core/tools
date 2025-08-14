"""Tests for the download subcommand of nf-core tools"""

import os
import shutil
import unittest
from pathlib import Path
from unittest import mock

import pytest

from nf_core.pipelines.download import DownloadWorkflow
from nf_core.pipelines.download.singularity import (
    SingularityError,
    SingularityFetcher,
)

from ...utils import TEST_DATA_DIR, with_temporary_folder


class SingularityTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def use_caplog(self, caplog):
        self._caplog = caplog

    @property
    def logged_levels(self) -> list[str]:
        return [record.levelname for record in self._caplog.records]

    @property
    def logged_messages(self) -> list[str]:
        return [record.message for record in self._caplog.records]

    def __contains__(self, item: str) -> bool:
        """Allows to check for log messages easily using the in operator inside a test:
        assert 'my log message' in self
        """
        return any(record.message == item for record in self._caplog.records if self._caplog)

    #
    # Tests for 'singularity_pull_image'
    #
    # If Singularity is installed, but the container can't be accessed because it does not exist or there are access
    # restrictions, a RuntimeWarning is raised due to the unavailability of the image.
    @pytest.mark.skipif(
        shutil.which("singularity") is None and shutil.which("apptainer") is None,
        reason="Can't test what Singularity does if it's not installed.",
    )
    @with_temporary_folder
    @mock.patch("nf_core.pipelines.download.singularity.SingularityProgress")
    def test_singularity_pull_image_singularity_installed(self, tmp_dir, mock_progress):
        tmp_dir = Path(tmp_dir)
        singularity_fetcher = SingularityFetcher(
            outdir=tmp_dir,
            container_library=[],
            registry_set=[],
            container_cache_utilisation="none",
            container_cache_index=None,
        )
        singularity_fetcher.check_and_set_implementation()
        singularity_fetcher.progress = mock_progress()
        # Test successful pull
        assert singularity_fetcher.pull_image("hello-world", tmp_dir / "hello-world.sif", "docker.io") is True

        # Pull again, but now the image already exists
        assert singularity_fetcher.pull_image("hello-world", tmp_dir / "hello-world.sif", "docker.io") is False

        # Test successful pull with absolute URI (use tiny 3.5MB test container from the "Kogia" project: https://github.com/bschiffthaler/kogia)
        assert singularity_fetcher.pull_image("docker.io/bschiffthaler/sed", tmp_dir / "sed.sif", "docker.io") is True

        # Test successful pull with absolute oras:// URI
        assert (
            singularity_fetcher.pull_image(
                "oras://community.wave.seqera.io/library/umi-transfer:1.0.0--e5b0c1a65b8173b6",
                tmp_dir / "umi-transfer-oras.sif",
                "docker.io",
            )
            is True
        )

        # try pulling Docker container image with oras://
        with pytest.raises(SingularityError.NoSingularityContainerError):
            singularity_fetcher.pull_image(
                "oras://ghcr.io/matthiaszepper/umi-transfer:dev",
                tmp_dir / "umi-transfer-oras_impostor.sif",
                "docker.io",
            )

        # try to pull from non-existing registry (Name change hello-world_new.sif is needed, otherwise ImageExistsError is raised before attempting to pull.)
        with pytest.raises(SingularityError.RegistryNotFoundError):
            singularity_fetcher.pull_image(
                "hello-world",
                tmp_dir / "break_the_registry_test.sif",
                "register-this-domain-to-break-the-test.io",
            )

        # test Image not found for several registries
        with pytest.raises(SingularityError.ImageNotFoundError):
            singularity_fetcher.pull_image("a-container", tmp_dir / "acontainer.sif", "quay.io")

        with pytest.raises(SingularityError.ImageNotFoundError):
            singularity_fetcher.pull_image("a-container", tmp_dir / "acontainer.sif", "docker.io")

        with pytest.raises(SingularityError.ImageNotFoundError):
            singularity_fetcher.pull_image("a-container", tmp_dir / "acontainer.sif", "ghcr.io")

        # test Image not found for absolute URI.
        with pytest.raises(SingularityError.ImageNotFoundError):
            singularity_fetcher.pull_image(
                "docker.io/bschiffthaler/nothingtopullhere",
                tmp_dir / "nothingtopullhere.sif",
                "docker.io",
            )

        # Traffic from Github Actions to GitHub's Container Registry is unlimited, so no harm should be done here.
        with pytest.raises(SingularityError.InvalidTagError):
            singularity_fetcher.pull_image(
                "ewels/multiqc:go-rewrite",
                tmp_dir / "multiqc-go.sif",
                "ghcr.io",
            )

    #
    #
    # Tests for 'SingularityFetcher.fetch_containers'
    #
    @pytest.mark.skipif(
        shutil.which("singularity") is None and shutil.which("apptainer") is None,
        reason="Can't test what Singularity does if it's not installed.",
    )
    @with_temporary_folder
    @mock.patch("nf_core.utils.fetch_wf_config")
    def test_fetch_containers_singularity(self, tmp_path, mock_fetch_wf_config):
        tmp_path = Path(tmp_path)
        download_obj = DownloadWorkflow(
            pipeline="dummy",
            outdir=tmp_path,
            container_library=("mirage-the-imaginative-registry.io", "quay.io", "ghcr.io", "docker.io"),
            container_system="singularity",
        )
        download_obj.containers = [
            "helloworld",
            "helloooooooworld",
            "ewels/multiqc:gorewrite",
        ]
        assert len(download_obj.container_library) == 4
        # This list of fake container images should produce all kinds of ContainerErrors.
        # Test that they are all caught inside SingularityFetcher.fetch_containers().
        singularity_fetcher = SingularityFetcher(
            outdir=tmp_path,
            container_library=download_obj.container_library,
            registry_set=download_obj.registry_set,
            container_cache_utilisation="none",
            container_cache_index=None,
        )
        singularity_fetcher.fetch_containers(
            download_obj.containers,
            download_obj.containers_remote,
        )

    #
    # Tests for 'singularity.symlink_registries' function
    #

    # Simple file name with no registry in it
    @with_temporary_folder
    @mock.patch(
        "nf_core.pipelines.download.singularity.SingularityFetcher.check_and_set_implementation"
    )  # This is to make sure that we do not check for Singularity/Apptainer installation
    @mock.patch("pathlib.Path.mkdir")
    @mock.patch("pathlib.Path.symlink_to")
    @mock.patch("os.symlink")
    @mock.patch("os.open")
    @mock.patch("os.close")
    @mock.patch("pathlib.Path.name")
    @mock.patch("pathlib.Path.parent")
    def test_symlink_singularity_images(
        self,
        tmp_path,
        mock_dirname,
        mock_basename,
        mock_close,
        mock_open,
        mock_os_symlink,
        mock_symlink,
        mock_makedirs,
        mock_check_and_set_implementation,
    ):
        # Setup
        tmp_path = Path(tmp_path)
        with (
            mock.patch.object(Path, "name", new_callable=mock.PropertyMock) as mock_basename,
            mock.patch.object(Path, "parent", new_callable=mock.PropertyMock) as mock_dirname,
        ):
            mock_dirname.return_value = tmp_path / "path/to"
            mock_basename.return_value = "singularity-image.img"
            mock_open.return_value = 12  # file descriptor
            mock_close.return_value = 12  # file descriptor

            registries = [
                "quay.io",
                "community-cr-prod.seqera.io/docker/registry/v2",
                "depot.galaxyproject.org/singularity",
            ]
            fetcher = SingularityFetcher(
                outdir=tmp_path,
                container_library=[],
                registry_set=registries,
                container_cache_utilisation="none",
                container_cache_index=None,
            )

            fetcher.symlink_registries(tmp_path / "path/to/singularity-image.img")

            # Check that os.makedirs was called with the correct arguments
            mock_makedirs.assert_any_call(exist_ok=True)

            # Check that os.open was called with the correct arguments
            mock_open.assert_any_call(tmp_path / "path/to", os.O_RDONLY)

            # Check that os.symlink was called with the correct arguments
            expected_calls = [
                mock.call(
                    Path("./singularity-image.img"),
                    Path("./quay.io-singularity-image.img"),
                    dir_fd=12,
                ),
                mock.call(
                    Path("./singularity-image.img"),
                    Path("./community-cr-prod.seqera.io-docker-registry-v2-singularity-image.img"),
                    dir_fd=12,
                ),
                mock.call(
                    Path("./singularity-image.img"),
                    Path("./depot.galaxyproject.org-singularity-singularity-image.img"),
                    dir_fd=12,
                ),
            ]
            mock_os_symlink.assert_has_calls(expected_calls, any_order=True)

    # File name with registry in it
    @with_temporary_folder
    @mock.patch(
        "nf_core.pipelines.download.singularity.SingularityFetcher.check_and_set_implementation"
    )  # This is to make sure that we do not check for Singularity/Apptainer installation
    @mock.patch("pathlib.Path.mkdir")
    @mock.patch("pathlib.Path.symlink_to")
    @mock.patch("os.symlink")
    @mock.patch("os.open")
    @mock.patch("os.close")
    @mock.patch("re.sub")
    @mock.patch("pathlib.Path.name")
    @mock.patch("pathlib.Path.parent")
    def test_symlink_singularity_symlink_registries(
        self,
        tmp_path,
        mock_dirname,
        mock_basename,
        mock_resub,
        mock_close,
        mock_open,
        mock_os_symlink,
        mock_symlink,
        mock_makedirs,
        mock_check_and_set_implementation,
    ):
        tmp_path = Path(tmp_path)
        # Setup
        with (
            mock.patch.object(Path, "name", new_callable=mock.PropertyMock) as mock_basename,
            mock.patch.object(Path, "parent", new_callable=mock.PropertyMock) as mock_dirname,
        ):
            mock_resub.return_value = "singularity-image.img"
            mock_dirname.return_value = tmp_path / "path/to"
            mock_basename.return_value = "quay.io-singularity-image.img"
            mock_open.return_value = 12  # file descriptor
            mock_close.return_value = 12  # file descriptor

            # Call the method with registry name included - should not happen, but preserve it then.

            registries = [
                "quay.io",  # Same as in the filename
                "community-cr-prod.seqera.io/docker/registry/v2",
            ]
            fetcher = SingularityFetcher(
                outdir=tmp_path,
                container_library=[],
                registry_set=registries,
                container_cache_utilisation="none",
                container_cache_index=None,
            )
            fetcher.symlink_registries(tmp_path / "path/to/quay.io-singularity-image.img")

            # Check that os.makedirs was called with the correct arguments
            mock_makedirs.assert_called_once_with(exist_ok=True)

            # Check that os.symlink was called with the correct arguments
            # assert_called_once_with also tells us that there was no attempt to
            # - symlink to itself
            # - symlink to the same registry
            mock_os_symlink.assert_called_once_with(
                Path("./quay.io-singularity-image.img"),
                Path(
                    "./community-cr-prod.seqera.io-docker-registry-v2-singularity-image.img"
                ),  # "quay.io-" has been trimmed
                dir_fd=12,
            )

            # Normally it would be called for each registry, but since quay.io is part of the name, it
            # will only be called once, as no symlink to itself must be created.
            mock_open.assert_called_once_with(tmp_path / "path/to", os.O_RDONLY)

    #
    # Tests for 'SingularityFetcher.pull_image'
    #
    @pytest.mark.skipif(
        shutil.which("singularity") is None and shutil.which("apptainer") is None,
        reason="Can't test what Singularity does if it's not installed.",
    )
    @with_temporary_folder
    @mock.patch("nf_core.pipelines.download.singularity.SingularityProgress")
    def test_singularity_pull_image_successfully(self, tmp_dir, mock_progress):
        tmp_dir = Path(tmp_dir)
        singularity_fetcher = SingularityFetcher(
            outdir=tmp_dir,
            container_library=[],
            registry_set=[],
            container_cache_utilisation="none",
            container_cache_index=None,
        )
        singularity_fetcher.check_and_set_implementation()
        singularity_fetcher.progress = mock_progress()
        singularity_fetcher.pull_image("hello-world", tmp_dir / "yet-another-hello-world.sif", "docker.io")

    #
    @with_temporary_folder
    @mock.patch("nf_core.utils.fetch_wf_config")
    def test_gather_registries(self, tmp_path, mock_fetch_wf_config):
        tmp_path = Path(tmp_path)
        download_obj = DownloadWorkflow(
            pipeline="dummy",
            outdir=tmp_path,
            container_library=None,
        )
        mock_fetch_wf_config.return_value = {
            "apptainer.registry": "apptainer-registry.io",
            "docker.registry": "docker.io",
            "podman.registry": "podman-registry.io",
            "singularity.registry": "singularity-registry.io",
            "someother.registry": "fake-registry.io",
        }
        download_obj.gather_registries(tmp_path)
        assert download_obj.registry_set
        assert isinstance(download_obj.registry_set, set)
        assert len(download_obj.registry_set) == 8

        assert "quay.io" in download_obj.registry_set  # default registry, if no container library is provided.
        assert (
            "depot.galaxyproject.org/singularity" in download_obj.registry_set
        )  # default registry, often hardcoded in modules
        assert "community.wave.seqera.io/library" in download_obj.registry_set  # Seqera containers Docker
        assert (
            "community-cr-prod.seqera.io/docker/registry/v2" in download_obj.registry_set
        )  # Seqera containers Singularity https:// download
        assert "apptainer-registry.io" in download_obj.registry_set
        assert "docker.io" in download_obj.registry_set
        assert "podman-registry.io" in download_obj.registry_set
        assert "singularity-registry.io" in download_obj.registry_set
        # it should only pull the apptainer, docker, podman and singularity registry from the config, but not any registry.
        assert "fake-registry.io" not in download_obj.registry_set

    #
    # If Singularity is not installed, it raises a OSError because the singularity command can't be found.
    #
    @pytest.mark.skipif(
        shutil.which("singularity") is not None or shutil.which("apptainer") is not None,
        reason="Can't test how the code behaves when singularity is not installed if it is.",
    )
    @with_temporary_folder
    @mock.patch("rich.progress.Progress.add_task")
    def test_singularity_pull_image_singularity_not_installed(self, tmp_dir, mock_rich_progress):
        tmp_dir = Path(tmp_dir)
        fetcher = SingularityFetcher(
            outdir=tmp_dir,
            container_library=[],
            registry_set=[],
            container_cache_utilisation="none",
            container_cache_index=None,
        )
        with pytest.raises(OSError):
            fetcher.check_and_set_implementation()

    #
    # Test for 'singularity.get_container_filename' function
    #

    @mock.patch("nf_core.pipelines.download.singularity.SingularityFetcher.check_and_set_implementation")
    def test_singularity_get_container_filename(self, mock_check_and_set_implementation):
        registries = [
            "docker.io",
            "quay.io",
            "depot.galaxyproject.org/singularity",
            "community.wave.seqera.io/library",
            "community-cr-prod.seqera.io/docker/registry/v2",
        ]

        fetcher = SingularityFetcher(
            outdir=Path("test_singularity_get_container_filename"),
            container_library=[],
            registry_set=registries,
            container_cache_utilisation="none",
            container_cache_index=None,
        )
        # Test --- galaxy URL #
        result = fetcher.get_container_filename(
            "https://depot.galaxyproject.org/singularity/bbmap:38.93--he522d1c_0",
        )
        assert result == "bbmap-38.93--he522d1c_0.img"

        # Test --- mulled containers #
        result = fetcher.get_container_filename(
            "quay.io/biocontainers/mulled-v2-1fa26d1ce03c295fe2fdcf85831a92fbcbd7e8c2:59cdd445419f14abac76b31dd0d71217994cbcc9-0",
        )
        assert (
            result
            == "biocontainers-mulled-v2-1fa26d1ce03c295fe2fdcf85831a92fbcbd7e8c2-59cdd445419f14abac76b31dd0d71217994cbcc9-0.img"
        )

        # Test --- Docker containers without registry #
        result = fetcher.get_container_filename("nf-core/ubuntu:20.04")
        assert result == "nf-core-ubuntu-20.04.img"

        # Test --- Docker container with explicit registry -> should be trimmed #
        result = fetcher.get_container_filename("docker.io/nf-core/ubuntu:20.04")
        assert result == "nf-core-ubuntu-20.04.img"

        # Test --- Docker container with explicit registry not in registry list -> can't be trimmed
        result = fetcher.get_container_filename("mirage-the-imaginative-registry.io/nf-core/ubuntu:20.04")
        assert result == "mirage-the-imaginative-registry.io-nf-core-ubuntu-20.04.img"

        # Test --- Seqera Docker containers: Trimmed, because it is hard-coded in the registry set.
        result = fetcher.get_container_filename("community.wave.seqera.io/library/coreutils:9.5--ae99c88a9b28c264")
        assert result == "coreutils-9.5--ae99c88a9b28c264.img"

        # Test --- Seqera Singularity containers: Trimmed, because it is hard-coded in the registry set.
        result = fetcher.get_container_filename(
            "https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/c2/c262fc09eca59edb5a724080eeceb00fb06396f510aefb229c2d2c6897e63975/data",
        )
        assert result == "blobs-sha256-c2-c262fc09eca59edb5a724080eeceb00fb06396f510aefb229c2d2c6897e63975-data.img"

        # Test --- Seqera Oras containers: Trimmed, because it is hard-coded in the registry set.
        result = fetcher.get_container_filename(
            "oras://community.wave.seqera.io/library/umi-transfer:1.0.0--e5b0c1a65b8173b6",
        )
        assert result == "umi-transfer-1.0.0--e5b0c1a65b8173b6.img"

        # Test --- SIF Singularity container with explicit registry -> should be trimmed #
        result = fetcher.get_container_filename(
            "docker.io-hashicorp-vault-1.16-sha256:e139ff28c23e1f22a6e325696318141259b177097d8e238a3a4c5b84862fadd8.sif",
        )
        assert (
            result == "hashicorp-vault-1.16-sha256-e139ff28c23e1f22a6e325696318141259b177097d8e238a3a4c5b84862fadd8.sif"
        )

        # Test --- SIF Singularity container without registry #
        result = fetcher.get_container_filename(
            "singularity-hpc/shpc/tests/testdata/salad_latest.sif",
        )
        assert result == "singularity-hpc-shpc-tests-testdata-salad_latest.sif"

        # Test --- Singularity container from a Singularity registry (and version tag) #
        result = fetcher.get_container_filename(
            "library://pditommaso/foo/bar.sif:latest",
        )
        assert result == "pditommaso-foo-bar-latest.sif"

        # Test --- galaxy URL but no registry given #
        fetcher.registry_set = []
        result = fetcher.get_container_filename("https://depot.galaxyproject.org/singularity/bbmap:38.93--he522d1c_0")
        assert result == "depot.galaxyproject.org-singularity-bbmap-38.93--he522d1c_0.img"

    #
    # Test for '--singularity-cache remote --singularity-cache-index'. Provide a list of containers already available in a remote location.
    #
    @with_temporary_folder
    def test_remote_container_functionality(self, tmp_dir):
        tmp_dir = Path(tmp_dir)
        os.environ["NXF_SINGULARITY_CACHEDIR"] = str(tmp_dir / "foo")

        download_obj = DownloadWorkflow(
            pipeline="nf-core/rnaseq",
            outdir=(tmp_dir / "new"),
            revision="3.9",
            compress_type="none",
            container_cache_index=Path(TEST_DATA_DIR, "testdata_remote_containers.txt"),
            container_system="singularity",
        )

        download_obj.include_configs = False  # suppress prompt, because stderr.is_interactive doesn't.

        # test if the settings are changed to mandatory defaults, if an external cache index is used.
        assert download_obj.container_cache_utilisation == "remote" and download_obj.container_system == "singularity"
        assert isinstance(download_obj.containers_remote, list) and len(download_obj.containers_remote) == 0
        # read in the file
        containers_remote = SingularityFetcher.read_remote_singularity_containers(download_obj.container_cache_index)
        assert len(containers_remote) == 33
        assert "depot.galaxyproject.org-singularity-salmon-1.5.2--h84f40af_0.img" in containers_remote
        assert "MV Rena" not in containers_remote  # decoy in test file
