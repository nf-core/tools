"""Tests for the download subcommand of nf-core tools
"""

import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pytest

import nf_core.create
import nf_core.utils
from nf_core.download import ContainerError, DownloadWorkflow, WorkflowRepo
from nf_core.synced_repo import SyncedRepo
from nf_core.utils import run_cmd

from .utils import with_temporary_folder


class DownloadTest(unittest.TestCase):
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

    # If Singularity is not installed, it raises a OSError because the singularity command can't be found.
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
    # Test Download for Tower
    #
    @with_temporary_folder
    @mock.patch("nf_core.download.DownloadWorkflow.get_singularity_images")
    def test_download_workflow_for_tower(self, tmp_dir, _):
        download_obj = DownloadWorkflow(
            pipeline="nf-core/rnaseq",
            revision=("3.7", "3.9"),
            compress_type="none",
            tower=True,
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

        # download_obj.wf_download_url is not set for tower downloads, but the sha values are
        assert isinstance(download_obj.wf_sha, dict) and len(download_obj.wf_sha) == 2
        assert isinstance(download_obj.wf_download_url, dict) and len(download_obj.wf_download_url) == 0

        # The outdir for multiple revisions is the pipeline name and date: e.g. nf-core-rnaseq_2023-04-27_18-54
        assert bool(re.search(r"nf-core-rnaseq_\d{4}-\d{2}-\d{1,2}_\d{1,2}-\d{1,2}", download_obj.outdir, re.S))

        download_obj.output_filename = f"{download_obj.outdir}.git"
        download_obj.download_workflow_tower(location=tmp_dir)

        assert download_obj.workflow_repo
        assert isinstance(download_obj.workflow_repo, WorkflowRepo)
        assert issubclass(type(download_obj.workflow_repo), SyncedRepo)

        # corroborate that the other revisions are inaccessible to the user.
        all_tags = {tag.name for tag in download_obj.workflow_repo.tags}
        all_heads = {head.name for head in download_obj.workflow_repo.heads}

        assert set(download_obj.revision) == all_tags
        # assert that the download has a "latest" branch.
        assert "latest" in all_heads

        # download_obj.download_workflow_tower(location=tmp_dir) will run container image detection for all requested revisions
        assert isinstance(download_obj.containers, list) and len(download_obj.containers) == 33
        assert (
            "https://depot.galaxyproject.org/singularity/bbmap:38.93--he522d1c_0" in download_obj.containers
        )  # direct definition
        assert (
            "https://depot.galaxyproject.org/singularity/mulled-v2-1fa26d1ce03c295fe2fdcf85831a92fbcbd7e8c2:59cdd445419f14abac76b31dd0d71217994cbcc9-0"
            in download_obj.containers
        )  # indirect definition via $container variable.
