"""Tests for the download subcommand of nf-core tools"""

import logging
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import List
from unittest import mock

import pytest

import nf_core.create
import nf_core.utils
from nf_core.download import ContainerError, DownloadWorkflow, WorkflowRepo
from nf_core.synced_repo import SyncedRepo
from nf_core.utils import run_cmd

from .utils import with_temporary_folder


class DownloadTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def use_caplog(self, caplog):
        self._caplog = caplog

    @property
    def logged_levels(self) -> List[str]:
        return [record.levelname for record in self._caplog.records]

    @property
    def logged_messages(self) -> List[str]:
        return [record.message for record in self._caplog.records]

    def __contains__(self, item: str) -> bool:
        """Allows to check for log messages easily using the in operator inside a test:
        assert 'my log message' in self
        """
        return any(record.message == item for record in self._caplog.records if self._caplog)

    #
    # Tests for 'get_release_hash'
    #
    def test_get_release_hash_release(self):
        wfs = nf_core.list.Workflows()
        wfs.get_remote_workflows()
        pipeline = "methylseq"
        download_obj = DownloadWorkflow(pipeline=pipeline, revision="1.6")
        (
            download_obj.pipeline,
            download_obj.wf_revisions,
            download_obj.wf_branches,
        ) = nf_core.utils.get_repo_releases_branches(pipeline, wfs)
        download_obj.get_revision_hash()
        assert download_obj.wf_sha[download_obj.revision[0]] == "b3e5e3b95aaf01d98391a62a10a3990c0a4de395"
        assert download_obj.outdir == "nf-core-methylseq_1.6"
        assert (
            download_obj.wf_download_url[download_obj.revision[0]]
            == "https://github.com/nf-core/methylseq/archive/b3e5e3b95aaf01d98391a62a10a3990c0a4de395.zip"
        )

    def test_get_release_hash_branch(self):
        wfs = nf_core.list.Workflows()
        wfs.get_remote_workflows()
        # Exoseq pipeline is archived, so `dev` branch should be stable
        pipeline = "exoseq"
        download_obj = DownloadWorkflow(pipeline=pipeline, revision="dev")
        (
            download_obj.pipeline,
            download_obj.wf_revisions,
            download_obj.wf_branches,
        ) = nf_core.utils.get_repo_releases_branches(pipeline, wfs)
        download_obj.get_revision_hash()
        assert download_obj.wf_sha[download_obj.revision[0]] == "819cbac792b76cf66c840b567ed0ee9a2f620db7"
        assert download_obj.outdir == "nf-core-exoseq_dev"
        assert (
            download_obj.wf_download_url[download_obj.revision[0]]
            == "https://github.com/nf-core/exoseq/archive/819cbac792b76cf66c840b567ed0ee9a2f620db7.zip"
        )

    def test_get_release_hash_non_existent_release(self):
        wfs = nf_core.list.Workflows()
        wfs.get_remote_workflows()
        pipeline = "methylseq"
        download_obj = DownloadWorkflow(pipeline=pipeline, revision="thisisfake")
        (
            download_obj.pipeline,
            download_obj.wf_revisions,
            download_obj.wf_branches,
        ) = nf_core.utils.get_repo_releases_branches(pipeline, wfs)
        with pytest.raises(AssertionError):
            download_obj.get_revision_hash()

    #
    # Tests for 'download_wf_files'
    #
    @with_temporary_folder
    def test_download_wf_files(self, outdir):
        download_obj = DownloadWorkflow(pipeline="nf-core/methylseq", revision="1.6")
        download_obj.outdir = outdir
        download_obj.wf_sha = {"1.6": "b3e5e3b95aaf01d98391a62a10a3990c0a4de395"}
        download_obj.wf_download_url = {
            "1.6": "https://github.com/nf-core/methylseq/archive/b3e5e3b95aaf01d98391a62a10a3990c0a4de395.zip"
        }
        rev = download_obj.download_wf_files(
            download_obj.revision[0],
            download_obj.wf_sha[download_obj.revision[0]],
            download_obj.wf_download_url[download_obj.revision[0]],
        )
        assert os.path.exists(os.path.join(outdir, rev, "main.nf"))

    #
    # Tests for 'download_configs'
    #
    @with_temporary_folder
    def test_download_configs(self, outdir):
        download_obj = DownloadWorkflow(pipeline="nf-core/methylseq", revision="1.6")
        download_obj.outdir = outdir
        download_obj.download_configs()
        assert os.path.exists(os.path.join(outdir, "configs", "nfcore_custom.config"))

    #
    # Tests for 'wf_use_local_configs'
    #
    @with_temporary_folder
    def test_wf_use_local_configs(self, tmp_path):
        # Get a workflow and configs
        test_pipeline_dir = os.path.join(tmp_path, "nf-core-testpipeline")
        create_obj = nf_core.create.PipelineCreate(
            "testpipeline",
            "This is a test pipeline",
            "Test McTestFace",
            no_git=True,
            outdir=test_pipeline_dir,
            plain=True,
        )
        create_obj.init_pipeline()

        with tempfile.TemporaryDirectory() as test_outdir:
            download_obj = DownloadWorkflow(pipeline="dummy", revision="1.2.0", outdir=test_outdir)
            shutil.copytree(test_pipeline_dir, os.path.join(test_outdir, "workflow"))
            download_obj.download_configs()

            # Test the function
            download_obj.wf_use_local_configs("workflow")
            wf_config = nf_core.utils.fetch_wf_config(os.path.join(test_outdir, "workflow"), cache_config=False)
            assert wf_config["params.custom_config_base"] == f"{test_outdir}/workflow/../configs/"

    #
    # Tests for 'find_container_images'
    #
    @with_temporary_folder
    @mock.patch("nf_core.utils.fetch_wf_config")
    def test_find_container_images_config_basic(self, tmp_path, mock_fetch_wf_config):
        download_obj = DownloadWorkflow(pipeline="dummy", outdir=tmp_path)
        mock_fetch_wf_config.return_value = {
            "process.mapping.container": "cutting-edge-container",
            "process.nocontainer": "not-so-cutting-edge",
        }
        download_obj.find_container_images("workflow")
        assert len(download_obj.containers) == 1
        assert download_obj.containers[0] == "cutting-edge-container"

    #
    # Test for 'find_container_images' in config with nextflow
    #
    @pytest.mark.skipif(
        shutil.which("nextflow") is None,
        reason="Can't run test that requires nextflow to run if not installed.",
    )
    @with_temporary_folder
    @mock.patch("nf_core.utils.fetch_wf_config")
    def test__find_container_images_config_nextflow(self, tmp_path, mock_fetch_wf_config):
        download_obj = DownloadWorkflow(pipeline="dummy", outdir=tmp_path)
        result = run_cmd("nextflow", f"config -flat {Path(__file__).resolve().parent / 'data/mock_config_containers'}")
        if result is not None:
            nfconfig_raw, _ = result
            config = {}
            for line in nfconfig_raw.splitlines():
                ul = line.decode("utf-8")
                try:
                    k, v = ul.split(" = ", 1)
                    config[k] = v.strip("'\"")
                except ValueError:
                    pass
            mock_fetch_wf_config.return_value = config
            download_obj.find_container_images("workflow")
            assert len(download_obj.containers) == 4
            assert "nfcore/methylseq:1.0" in download_obj.containers
            assert "nfcore/methylseq:1.4" in download_obj.containers
            assert "nfcore/sarek:dev" in download_obj.containers
            assert (
                "https://depot.galaxyproject.org/singularity/r-shinyngs:1.7.1--r42hdfd78af_1" in download_obj.containers
            )
            # does not yet pick up nfcore/sarekvep:dev.${params.genome}, because that is no valid URL or Docker URI.

    #
    # Test for 'find_container_images' in modules
    #
    @with_temporary_folder
    @mock.patch("nf_core.utils.fetch_wf_config")
    def test_find_container_images_modules(self, tmp_path, mock_fetch_wf_config):
        download_obj = DownloadWorkflow(pipeline="dummy", outdir=tmp_path)
        mock_fetch_wf_config.return_value = {}
        download_obj.find_container_images(Path(__file__).resolve().parent / "data/mock_module_containers")

        # mock_docker_single_quay_io.nf
        assert "quay.io/biocontainers/singlequay:1.9--pyh9f0ad1d_0" in download_obj.containers

        # mock_dsl2_apptainer_var1.nf (possible future convention?)
        assert (
            "https://depot.galaxyproject.org/singularity/dsltwoapptainervarone:1.1.0--py38h7be5676_2"
            in download_obj.containers
        )
        assert "biocontainers/dsltwoapptainervarone:1.1.0--py38h7be5676_2" not in download_obj.containers

        # mock_dsl2_apptainer_var2.nf (possible future convention?)
        assert (
            "https://depot.galaxyproject.org/singularity/dsltwoapptainervartwo:1.1.0--hdfd78af_0"
            in download_obj.containers
        )
        assert "biocontainers/dsltwoapptainervartwo:1.1.0--hdfd78af_0" not in download_obj.containers

        # mock_dsl2_current_inverted.nf (new implementation supports if the direct download URL is listed after Docker URI)
        assert (
            "https://depot.galaxyproject.org/singularity/dsltwocurrentinv:3.3.2--h1b792b2_1" in download_obj.containers
        )
        assert "biocontainers/dsltwocurrentinv:3.3.2--h1b792b2_1" not in download_obj.containers

        # mock_dsl2_current.nf (main nf-core convention, should be the one in far the most modules)
        assert (
            "https://depot.galaxyproject.org/singularity/dsltwocurrent:1.2.1--pyhdfd78af_0" in download_obj.containers
        )
        assert "biocontainers/dsltwocurrent:1.2.1--pyhdfd78af_0" not in download_obj.containers

        # mock_dsl2_old.nf (initial DSL2 convention)
        assert "https://depot.galaxyproject.org/singularity/dsltwoold:0.23.0--0" in download_obj.containers
        assert "quay.io/biocontainers/dsltwoold:0.23.0--0" not in download_obj.containers

        # mock_dsl2_variable.nf (currently the edgiest edge case supported)
        assert (
            "https://depot.galaxyproject.org/singularity/mulled-v2-1fa26d1ce03c295fe2fdcf85831a92fbcbd7e8c2:59cdd445419f14abac76b31dd0d71217994cbcc9-0"
            in download_obj.containers
        )
        assert (
            "https://depot.galaxyproject.org/singularity/mulled-v2-1fa26d1ce03c295fe2fdcf85831a92fbcbd7e8c2:afaaa4c6f5b308b4b6aa2dd8e99e1466b2a6b0cd-0"
            in download_obj.containers
        )
        assert (
            "quay.io/biocontainers/mulled-v2-1fa26d1ce03c295fe2fdcf85831a92fbcbd7e8c2:59cdd445419f14abac76b31dd0d71217994cbcc9-0"
            not in download_obj.containers
        )
        assert (
            "quay.io/biocontainers/mulled-v2-1fa26d1ce03c295fe2fdcf85831a92fbcbd7e8c2:afaaa4c6f5b308b4b6aa2dd8e99e1466b2a6b0cd-0"
            not in download_obj.containers
        )

    #
    # Tests for 'singularity_pull_image'
    #
    # If Singularity is installed, but the container can't be accessed because it does not exist or there are access
    # restrictions, a RuntimeWarning is raised due to the unavailability of the image.
    @pytest.mark.skipif(
        shutil.which("singularity") is None,
        reason="Can't test what Singularity does if it's not installed.",
    )
    @with_temporary_folder
    @mock.patch("rich.progress.Progress.add_task")
    def test_singularity_pull_image_singularity_installed(self, tmp_dir, mock_rich_progress):
        download_obj = DownloadWorkflow(pipeline="dummy", outdir=tmp_dir)

        # Test successful pull
        download_obj.singularity_pull_image(
            "hello-world", f"{tmp_dir}/hello-world.sif", None, "docker.io", mock_rich_progress
        )

        # Pull again, but now the image already exists
        with pytest.raises(ContainerError.ImageExistsError):
            download_obj.singularity_pull_image(
                "hello-world", f"{tmp_dir}/hello-world.sif", None, "docker.io", mock_rich_progress
            )

        # Test successful pull with absolute URI (use tiny 3.5MB test container from the "Kogia" project: https://github.com/bschiffthaler/kogia)
        download_obj.singularity_pull_image(
            "docker.io/bschiffthaler/sed", f"{tmp_dir}/sed.sif", None, "docker.io", mock_rich_progress
        )

        # try to pull from non-existing registry (Name change hello-world_new.sif is needed, otherwise ImageExistsError is raised before attempting to pull.)
        with pytest.raises(ContainerError.RegistryNotFoundError):
            download_obj.singularity_pull_image(
                "hello-world",
                f"{tmp_dir}/hello-world_new.sif",
                None,
                "register-this-domain-to-break-the-test.io",
                mock_rich_progress,
            )

        # test Image not found for several registries
        with pytest.raises(ContainerError.ImageNotFoundError):
            download_obj.singularity_pull_image(
                "a-container", f"{tmp_dir}/acontainer.sif", None, "quay.io", mock_rich_progress
            )

        with pytest.raises(ContainerError.ImageNotFoundError):
            download_obj.singularity_pull_image(
                "a-container", f"{tmp_dir}/acontainer.sif", None, "docker.io", mock_rich_progress
            )

        with pytest.raises(ContainerError.ImageNotFoundError):
            download_obj.singularity_pull_image(
                "a-container", f"{tmp_dir}/acontainer.sif", None, "ghcr.io", mock_rich_progress
            )

        # test Image not found for absolute URI.
        with pytest.raises(ContainerError.ImageNotFoundError):
            download_obj.singularity_pull_image(
                "docker.io/bschiffthaler/nothingtopullhere",
                f"{tmp_dir}/nothingtopullhere.sif",
                None,
                "docker.io",
                mock_rich_progress,
            )

        # Traffic from Github Actions to GitHub's Container Registry is unlimited, so no harm should be done here.
        with pytest.raises(ContainerError.InvalidTagError):
            download_obj.singularity_pull_image(
                "ewels/multiqc:go-rewrite",
                f"{tmp_dir}/umi-transfer.sif",
                None,
                "ghcr.io",
                mock_rich_progress,
            )

    @pytest.mark.skipif(
        shutil.which("singularity") is None,
        reason="Can't test what Singularity does if it's not installed.",
    )
    @with_temporary_folder
    @mock.patch("rich.progress.Progress.add_task")
    def test_singularity_pull_image_successfully(self, tmp_dir, mock_rich_progress):
        download_obj = DownloadWorkflow(pipeline="dummy", outdir=tmp_dir)
        download_obj.singularity_pull_image(
            "hello-world", f"{tmp_dir}/yet-another-hello-world.sif", None, "docker.io", mock_rich_progress
        )

    #
    # Tests for 'get_singularity_images'
    #
    @pytest.mark.skipif(
        shutil.which("singularity") is None,
        reason="Can't test what Singularity does if it's not installed.",
    )
    @with_temporary_folder
    @mock.patch("nf_core.utils.fetch_wf_config")
    def test_get_singularity_images(self, tmp_path, mock_fetch_wf_config):
        download_obj = DownloadWorkflow(
            pipeline="dummy",
            outdir=tmp_path,
            container_library=("mirage-the-imaginative-registry.io", "quay.io", "ghcr.io", "docker.io"),
        )
        mock_fetch_wf_config.return_value = {
            "process.helloworld.container": "helloworld",
            "process.hellooworld.container": "helloooooooworld",
            "process.mapping.container": "ewels/multiqc:gorewrite",
        }
        download_obj.find_container_images("workflow")
        assert len(download_obj.container_library) == 4
        # This list of fake container images should produce all kinds of ContainerErrors.
        # Test that they are all caught inside get_singularity_images().
        download_obj.get_singularity_images()

    @with_temporary_folder
    @mock.patch("os.makedirs")
    @mock.patch("os.symlink")
    @mock.patch("os.open")
    @mock.patch("os.close")
    @mock.patch("re.sub")
    @mock.patch("os.path.basename")
    @mock.patch("os.path.dirname")
    def test_symlink_singularity_images(
        self,
        tmp_path,
        mock_dirname,
        mock_basename,
        mock_resub,
        mock_close,
        mock_open,
        mock_symlink,
        mock_makedirs,
    ):
        # Setup
        mock_resub.return_value = "singularity-image.img"
        mock_dirname.return_value = f"{tmp_path}/path/to"
        mock_basename.return_value = "quay.io-singularity-image.img"
        mock_open.return_value = 12  # file descriptor
        mock_close.return_value = 12  # file descriptor

        download_obj = DownloadWorkflow(
            pipeline="dummy",
            outdir=tmp_path,
            container_library=("mirage-the-imaginative-registry.io", "quay.io"),
        )

        # Call the method
        download_obj.symlink_singularity_images(f"{tmp_path}/path/to/quay.io-singularity-image.img")
        print(mock_resub.call_args)

        # Check that os.makedirs was called with the correct arguments
        mock_makedirs.assert_any_call(f"{tmp_path}/path/to", exist_ok=True)

        # Check that os.open was called with the correct arguments
        mock_open.assert_called_once_with(f"{tmp_path}/path/to", os.O_RDONLY)

        # Check that os.symlink was called with the correct arguments
        mock_symlink.assert_any_call(
            "./quay.io-singularity-image.img",
            "./mirage-the-imaginative-registry.io-quay.io-singularity-image.img",
            dir_fd=12,
        )
        # Check that there is no attempt to symlink to itself (test parameters would result in that behavior if not checked in the function)
        assert (
            unittest.mock.call("./quay.io-singularity-image.img", "./quay.io-singularity-image.img", dir_fd=12)
            not in mock_symlink.call_args_list
        )

    #
    # Test for gather_registries'
    #
    @with_temporary_folder
    @mock.patch("nf_core.utils.fetch_wf_config")
    def test_gather_registries(self, tmp_path, mock_fetch_wf_config):
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
        assert len(download_obj.registry_set) == 6

        assert "quay.io" in download_obj.registry_set  # default registry, if no container library is provided.
        assert "depot.galaxyproject.org" in download_obj.registry_set  # default registry, often hardcoded in modules
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
        shutil.which("singularity") is not None,
        reason="Can't test how the code behaves when singularity is not installed if it is.",
    )
    @with_temporary_folder
    @mock.patch("rich.progress.Progress.add_task")
    def test_singularity_pull_image_singularity_not_installed(self, tmp_dir, mock_rich_progress):
        download_obj = DownloadWorkflow(pipeline="dummy", outdir=tmp_dir)
        with pytest.raises(OSError):
            download_obj.singularity_pull_image(
                "a-container", f"{tmp_dir}/anothercontainer.sif", None, "quay.io", mock_rich_progress
            )

    #
    # Test for 'singularity_image_filenames' function
    #
    @with_temporary_folder
    def test_singularity_image_filenames(self, tmp_path):
        os.environ["NXF_SINGULARITY_CACHEDIR"] = f"{tmp_path}/cachedir"

        download_obj = DownloadWorkflow(pipeline="dummy", outdir=tmp_path)
        download_obj.outdir = tmp_path
        download_obj.container_cache_utilisation = "amend"
        download_obj.registry_set = {"docker.io", "quay.io", "depot.galaxyproject.org"}

        ## Test phase I: Container not yet cached, should be amended to cache
        # out_path: str, Path to cache
        # cache_path: None

        result = download_obj.singularity_image_filenames(
            "https://depot.galaxyproject.org/singularity/bbmap:38.93--he522d1c_0"
        )

        # Assert that the result is a tuple of length 2
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

        # Assert that the types of the elements are (str, None)
        self.assertTrue(all((isinstance(element, str), element is None) for element in result))

        # assert that the correct out_path is returned that points to the cache
        assert result[0].endswith("/cachedir/singularity-bbmap-38.93--he522d1c_0.img")

        ## Test phase II: Test various container names
        # out_path: str, Path to cache
        # cache_path: None
        result = download_obj.singularity_image_filenames(
            "quay.io/biocontainers/mulled-v2-1fa26d1ce03c295fe2fdcf85831a92fbcbd7e8c2:59cdd445419f14abac76b31dd0d71217994cbcc9-0"
        )
        assert result[0].endswith(
            "/cachedir/biocontainers-mulled-v2-1fa26d1ce03c295fe2fdcf85831a92fbcbd7e8c2-59cdd445419f14abac76b31dd0d71217994cbcc9-0.img"
        )

        result = download_obj.singularity_image_filenames("nf-core/ubuntu:20.04")
        assert result[0].endswith("/cachedir/nf-core-ubuntu-20.04.img")

        ## Test phase III: Container wil lbe cached but also copied to out_path
        # out_path: str, Path to cache
        # cache_path: str, Path to cache
        download_obj.container_cache_utilisation = "copy"
        result = download_obj.singularity_image_filenames(
            "https://depot.galaxyproject.org/singularity/bbmap:38.93--he522d1c_0"
        )

        self.assertTrue(all(isinstance(element, str) for element in result))
        assert result[0].endswith("/singularity-images/singularity-bbmap-38.93--he522d1c_0.img")
        assert result[1].endswith("/cachedir/singularity-bbmap-38.93--he522d1c_0.img")

        ## Test phase IV: Expect an error if no NXF_SINGULARITY_CACHEDIR is defined
        os.environ["NXF_SINGULARITY_CACHEDIR"] = ""
        with self.assertRaises(FileNotFoundError):
            download_obj.singularity_image_filenames(
                "https://depot.galaxyproject.org/singularity/bbmap:38.93--he522d1c_0"
            )

    #
    # Test for '--singularity-cache remote --singularity-cache-index'. Provide a list of containers already available in a remote location.
    #
    @with_temporary_folder
    def test_remote_container_functionality(self, tmp_dir):
        os.environ["NXF_SINGULARITY_CACHEDIR"] = "foo"

        download_obj = DownloadWorkflow(
            pipeline="nf-core/rnaseq",
            outdir=os.path.join(tmp_dir, "new"),
            revision="3.9",
            compress_type="none",
            container_cache_index=Path(__file__).resolve().parent / "data/testdata_remote_containers.txt",
        )

        download_obj.include_configs = False  # suppress prompt, because stderr.is_interactive doesn't.

        # test if the settings are changed to mandatory defaults, if an external cache index is used.
        assert download_obj.container_cache_utilisation == "remote" and download_obj.container_system == "singularity"
        assert isinstance(download_obj.containers_remote, list) and len(download_obj.containers_remote) == 0
        # read in the file
        download_obj.read_remote_containers()
        assert len(download_obj.containers_remote) == 33
        assert "depot.galaxyproject.org-singularity-salmon-1.5.2--h84f40af_0.img" in download_obj.containers_remote
        assert "MV Rena" not in download_obj.containers_remote  # decoy in test file

    #
    # Tests for the main entry method 'download_workflow'
    #
    @with_temporary_folder
    @mock.patch("nf_core.download.DownloadWorkflow.singularity_pull_image")
    @mock.patch("shutil.which")
    def test_download_workflow_with_success(self, tmp_dir, mock_download_image, mock_singularity_installed):
        os.environ["NXF_SINGULARITY_CACHEDIR"] = "foo"

        download_obj = DownloadWorkflow(
            pipeline="nf-core/methylseq",
            outdir=os.path.join(tmp_dir, "new"),
            container_system="singularity",
            revision="1.6",
            compress_type="none",
            container_cache_utilisation="copy",
        )

        download_obj.include_configs = True  # suppress prompt, because stderr.is_interactive doesn't.
        download_obj.download_workflow()

    #
    # Test Download for Seqera Platform
    #
    @with_temporary_folder
    @mock.patch("nf_core.download.DownloadWorkflow.get_singularity_images")
    def test_download_workflow_for_platform(self, tmp_dir, _):
        download_obj = DownloadWorkflow(
            pipeline="nf-core/rnaseq",
            revision=("3.7", "3.9"),
            compress_type="none",
            platform=True,
            container_system="singularity",
        )

        download_obj.include_configs = False  # suppress prompt, because stderr.is_interactive doesn't.

        assert isinstance(download_obj.revision, list) and len(download_obj.revision) == 2
        assert isinstance(download_obj.wf_sha, dict) and len(download_obj.wf_sha) == 0
        assert isinstance(download_obj.wf_download_url, dict) and len(download_obj.wf_download_url) == 0

        wfs = nf_core.list.Workflows()
        wfs.get_remote_workflows()
        (
            download_obj.pipeline,
            download_obj.wf_revisions,
            download_obj.wf_branches,
        ) = nf_core.utils.get_repo_releases_branches(download_obj.pipeline, wfs)

        download_obj.get_revision_hash()

        # download_obj.wf_download_url is not set for Seqera Platform downloads, but the sha values are
        assert isinstance(download_obj.wf_sha, dict) and len(download_obj.wf_sha) == 2
        assert isinstance(download_obj.wf_download_url, dict) and len(download_obj.wf_download_url) == 0

        # The outdir for multiple revisions is the pipeline name and date: e.g. nf-core-rnaseq_2023-04-27_18-54
        assert bool(re.search(r"nf-core-rnaseq_\d{4}-\d{2}-\d{1,2}_\d{1,2}-\d{1,2}", download_obj.outdir, re.S))

        download_obj.output_filename = f"{download_obj.outdir}.git"
        download_obj.download_workflow_platform(location=tmp_dir)

        assert download_obj.workflow_repo
        assert isinstance(download_obj.workflow_repo, WorkflowRepo)
        assert issubclass(type(download_obj.workflow_repo), SyncedRepo)

        # corroborate that the other revisions are inaccessible to the user.
        all_tags = {tag.name for tag in download_obj.workflow_repo.tags}
        all_heads = {head.name for head in download_obj.workflow_repo.heads}

        assert set(download_obj.revision) == all_tags
        # assert that the download has a "latest" branch.
        assert "latest" in all_heads

        # download_obj.download_workflow_platform(location=tmp_dir) will run container image detection for all requested revisions
        assert isinstance(download_obj.containers, list) and len(download_obj.containers) == 33
        assert (
            "https://depot.galaxyproject.org/singularity/bbmap:38.93--he522d1c_0" in download_obj.containers
        )  # direct definition
        assert (
            "https://depot.galaxyproject.org/singularity/mulled-v2-1fa26d1ce03c295fe2fdcf85831a92fbcbd7e8c2:59cdd445419f14abac76b31dd0d71217994cbcc9-0"
            in download_obj.containers
        )  # indirect definition via $container variable.

    #
    # Brief test adding a single custom tag to Seqera Platform download
    #
    @mock.patch("nf_core.download.DownloadWorkflow.get_singularity_images")
    @with_temporary_folder
    def test_download_workflow_for_platform_with_one_custom_tag(self, _, tmp_dir):
        download_obj = DownloadWorkflow(
            pipeline="nf-core/rnaseq",
            revision=("3.9"),
            compress_type="none",
            platform=True,
            container_system=None,
            additional_tags=("3.9=cool_revision",),
        )
        assert isinstance(download_obj.additional_tags, list) and len(download_obj.additional_tags) == 1

    #
    # Test adding custom tags to Seqera Platform download (full test)
    #
    @mock.patch("nf_core.download.DownloadWorkflow.get_singularity_images")
    @with_temporary_folder
    def test_download_workflow_for_platform_with_custom_tags(self, _, tmp_dir):
        with self._caplog.at_level(logging.INFO):
            from git.refs.tag import TagReference

            download_obj = DownloadWorkflow(
                pipeline="nf-core/rnaseq",
                revision=("3.7", "3.9"),
                compress_type="none",
                platform=True,
                container_system=None,
                additional_tags=(
                    "3.7=a.tad.outdated",
                    "3.9=cool_revision",
                    "3.9=invalid tag",
                    "3.14.0=not_included",
                    "What is this?",
                ),
            )

            download_obj.include_configs = False  # suppress prompt, because stderr.is_interactive doesn't.

            assert isinstance(download_obj.revision, list) and len(download_obj.revision) == 2
            assert isinstance(download_obj.wf_sha, dict) and len(download_obj.wf_sha) == 0
            assert isinstance(download_obj.wf_download_url, dict) and len(download_obj.wf_download_url) == 0
            assert isinstance(download_obj.additional_tags, list) and len(download_obj.additional_tags) == 5

            wfs = nf_core.list.Workflows()
            wfs.get_remote_workflows()
            (
                download_obj.pipeline,
                download_obj.wf_revisions,
                download_obj.wf_branches,
            ) = nf_core.utils.get_repo_releases_branches(download_obj.pipeline, wfs)

            download_obj.get_revision_hash()
            download_obj.output_filename = f"{download_obj.outdir}.git"
            download_obj.download_workflow_platform(location=tmp_dir)

            assert download_obj.workflow_repo
            assert isinstance(download_obj.workflow_repo, WorkflowRepo)
            assert issubclass(type(download_obj.workflow_repo), SyncedRepo)
            assert "Locally cached repository: nf-core/rnaseq, revisions 3.7, 3.9" in repr(download_obj.workflow_repo)

            # assert that every additional tag has been passed on to the WorkflowRepo instance
            assert download_obj.additional_tags == download_obj.workflow_repo.additional_tags

            # assert that the additional tags are all TagReference objects
            assert all(isinstance(tag, TagReference) for tag in download_obj.workflow_repo.tags)

            workflow_repo_tags = {tag.name for tag in download_obj.workflow_repo.tags}
            assert len(workflow_repo_tags) == 4
            # the invalid/malformed additional_tags should not have been added.
            assert all(tag in workflow_repo_tags for tag in {"3.7", "a.tad.outdated", "cool_revision", "3.9"})
            assert not any(tag in workflow_repo_tags for tag in {"invalid tag", "not_included", "What is this?"})

            assert all(
                log in self.logged_messages
                for log in {
                    "[red]Could not apply invalid `--tag` specification[/]: '3.9=invalid tag'",
                    "[red]Adding tag 'not_included' to '3.14.0' failed.[/]\n Mind that '3.14.0' must be a valid git reference that resolves to a commit.",
                    "[red]Could not apply invalid `--tag` specification[/]: 'What is this?'",
                }
            )
