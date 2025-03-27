"""Tests for the download subcommand of nf-core tools"""

import logging
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import List
from unittest import mock

import pytest
import requests
import rich.progress_bar
import rich.table
import rich.text

import nf_core.pipelines.create.create
import nf_core.pipelines.list
import nf_core.utils
from nf_core.pipelines.download import DownloadWorkflow, WorkflowRepo
from nf_core.pipelines.downloads.singularity import (
    ContainerError,
    SingularityFetcher,
    get_container_filename,
    symlink_registries,
)
from nf_core.pipelines.downloads.utils import DownloadError, DownloadProgress, FileDownloader, intermediate_file
from nf_core.synced_repo import SyncedRepo
from nf_core.utils import run_cmd

from ..utils import TEST_DATA_DIR, with_temporary_folder


class DownloadUtilsTest(unittest.TestCase):
    #
    # Test for 'utils.intermediate_file'
    #
    @with_temporary_folder
    def test_intermediate_file(self, outdir):
        # Code that doesn't fail. The file shall exist

        # Directly write to the file, as in download_image
        output_path = os.path.join(outdir, "testfile1")
        with intermediate_file(output_path) as tmp:
            tmp_path = tmp.name
            tmp.write(b"Hello, World!")

        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) == 13
        assert not os.path.exists(tmp_path)

        # Run an external command as in pull_image
        output_path = os.path.join(outdir, "testfile2")
        with intermediate_file(output_path) as tmp:
            tmp_path = tmp.name
            subprocess.check_call([f"echo 'Hello, World!' > {tmp_path}"], shell=True)

        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) == 14  # Extra \n !
        assert not os.path.exists(tmp_path)

        # Code that fails. The file shall not exist

        # Directly write to the file and raise an exception
        output_path = os.path.join(outdir, "testfile3")
        with pytest.raises(ValueError):
            with intermediate_file(output_path) as tmp:
                tmp_path = tmp.name
                tmp.write(b"Hello, World!")
                raise ValueError("This is a test error")

        assert not os.path.exists(output_path)
        assert not os.path.exists(tmp_path)

        # Run an external command and raise an exception
        output_path = os.path.join(outdir, "testfile4")
        with pytest.raises(subprocess.CalledProcessError):
            with intermediate_file(output_path) as tmp:
                tmp_path = tmp.name
                subprocess.check_call([f"echo 'Hello, World!' > {tmp_path}"], shell=True)
                subprocess.check_call(["ls", "/dummy"])

        assert not os.path.exists(output_path)
        assert not os.path.exists(tmp_path)

        # Test for invalid output paths
        with pytest.raises(DownloadError):
            with intermediate_file(outdir) as tmp:
                pass

        output_path = os.path.join(outdir, "testfile5")
        os.symlink("/dummy", output_path)
        with pytest.raises(DownloadError):
            with intermediate_file(output_path) as tmp:
                pass

    #
    # Test for 'utils.DownloadProgress.add/update_main_task'
    #
    def test_download_progress_main_task(self):
        with DownloadProgress() as progress:
            # No task initially
            assert progress.tasks == []

            # Add a task, it should be there
            task_id = progress.add_main_task(total=42)
            assert task_id == 0
            assert len(progress.tasks) == 1
            assert progress.task_ids[0] == task_id
            assert progress.tasks[0].total == 42

            # Add another task, there should now be two
            other_task_id = progress.add_task("Another task", total=28)
            assert other_task_id == 1
            assert len(progress.tasks) == 2
            assert progress.task_ids[1] == other_task_id
            assert progress.tasks[1].total == 28

            progress.update_main_task(total=35)
            assert progress.tasks[0].total == 35
            assert progress.tasks[1].total == 28

    #
    # Test for 'utils.DownloadProgress.sub_task'
    #
    def test_download_progress_sub_task(self):
        with DownloadProgress() as progress:
            # No task initially
            assert progress.tasks == []

            # Add a sub-task, it should be there
            with progress.sub_task("Sub-task", total=42) as sub_task_id:
                assert sub_task_id == 0
                assert len(progress.tasks) == 1
                assert progress.task_ids[0] == sub_task_id
                assert progress.tasks[0].total == 42

            # The sub-task should be gone now
            assert progress.tasks == []

            # Add another sub-task, this time that raises an exception
            with pytest.raises(ValueError):
                with progress.sub_task("Sub-task", total=28) as sub_task_id:
                    assert sub_task_id == 1
                    assert len(progress.tasks) == 1
                    assert progress.task_ids[0] == sub_task_id
                    assert progress.tasks[0].total == 28
                    raise ValueError("This is a test error")

            # The sub-task should also be gone now
            assert progress.tasks == []

    #
    # Test for 'utils.DownloadProgress.get_renderables'
    #
    def test_download_progress_renderables(self):
        # Test the "singularity_pull" progress type
        with DownloadProgress() as progress:
            assert progress.tasks == []
            progress.add_task(
                "Task 1", progress_type="singularity_pull", total=42, completed=11, current_log="example log"
            )
            assert len(progress.tasks) == 1

            renderable = progress.get_renderable()
            assert isinstance(renderable, rich.console.Group), type(renderable)

            assert len(renderable.renderables) == 1
            table = renderable.renderables[0]
            assert isinstance(table, rich.table.Table)

            assert isinstance(table.columns[0]._cells[0], str)
            assert table.columns[0]._cells[0] == "[magenta]Task 1"

            assert isinstance(table.columns[1]._cells[0], str)
            assert table.columns[1]._cells[0] == "[blue]example log"

            assert isinstance(table.columns[2]._cells[0], rich.progress_bar.ProgressBar)
            assert table.columns[2]._cells[0].completed == 11
            assert table.columns[2]._cells[0].total == 42

        # Test the "summary" progress type
        with DownloadProgress() as progress:
            assert progress.tasks == []
            progress.add_task("Task 1", progress_type="summary", total=42, completed=11)
            assert len(progress.tasks) == 1

            renderable = progress.get_renderable()
            assert isinstance(renderable, rich.console.Group), type(renderable)

            assert len(renderable.renderables) == 1
            table = renderable.renderables[0]
            assert isinstance(table, rich.table.Table)

            assert isinstance(table.columns[0]._cells[0], str)
            assert table.columns[0]._cells[0] == "[magenta]Task 1"

            assert isinstance(table.columns[1]._cells[0], rich.progress_bar.ProgressBar)
            assert table.columns[1]._cells[0].completed == 11
            assert table.columns[1]._cells[0].total == 42

            assert isinstance(table.columns[2]._cells[0], str)
            assert table.columns[2]._cells[0] == "[progress.percentage] 26%"

            assert isinstance(table.columns[3]._cells[0], str)
            assert table.columns[3]._cells[0] == "•"

            assert isinstance(table.columns[4]._cells[0], str)
            assert table.columns[4]._cells[0] == "[green]11/42 completed"

        # Test the "download" progress type
        with DownloadProgress() as progress:
            assert progress.tasks == []
            progress.add_task("Task 1", progress_type="download", total=42, completed=11)
            assert len(progress.tasks) == 1

            renderable = progress.get_renderable()
            assert isinstance(renderable, rich.console.Group), type(renderable)

            assert len(renderable.renderables) == 1
            table = renderable.renderables[0]
            assert isinstance(table, rich.table.Table)

            assert isinstance(table.columns[0]._cells[0], str)
            assert table.columns[0]._cells[0] == "[blue]Task 1"

            assert isinstance(table.columns[1]._cells[0], rich.progress_bar.ProgressBar)
            assert table.columns[1]._cells[0].completed == 11
            assert table.columns[1]._cells[0].total == 42

            assert isinstance(table.columns[2]._cells[0], str)
            assert table.columns[2]._cells[0] == "[progress.percentage]26.2%"

            assert isinstance(table.columns[3]._cells[0], str)
            assert table.columns[3]._cells[0] == "•"

            assert isinstance(table.columns[4]._cells[0], rich.text.Text)
            assert table.columns[4]._cells[0]._text == ["11/42 bytes"]

            assert isinstance(table.columns[5]._cells[0], str)
            assert table.columns[5]._cells[0] == "•"

            assert isinstance(table.columns[6]._cells[0], rich.text.Text)
            assert table.columns[6]._cells[0]._text == ["?"]

    #
    # Test for 'utils.FileDownloader'
    #
    @with_temporary_folder
    def test_file_download(self, outdir):
        with DownloadProgress() as progress:
            # No task initially
            assert progress.tasks == []
            assert progress._task_index == 0

            # Download a file
            downloader = FileDownloader(progress)
            src_url = "https://github.com/nf-core/test-datasets/raw/refs/heads/modules/data/genomics/sarscov2/genome/genome.fasta.fai"
            output_path = os.path.join(outdir, os.path.basename(src_url))
            downloader.download_file(src_url, output_path)
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) == 27

            # A task was added but is now gone
            assert progress._task_index == 1
            assert progress.tasks == []

            # Invalid URL (schema)
            src_url = "dummy://github.com/nf-core/test-datasets/raw/refs/heads/modules/data/genomics/sarscov2/genome/genome.fasta.fax"
            output_path = os.path.join(outdir, os.path.basename(src_url))
            with pytest.raises(requests.exceptions.InvalidSchema):
                downloader.download_file(src_url, output_path)
            assert not os.path.exists(output_path)

            # A task was added but is now gone
            assert progress._task_index == 2
            assert progress.tasks == []


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
        wfs = nf_core.pipelines.list.Workflows()
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
        wfs = nf_core.pipelines.list.Workflows()
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

    def test_get_release_hash_long_commit(self):
        wfs = nf_core.pipelines.list.Workflows()
        wfs.get_remote_workflows()
        # Exoseq pipeline is archived, so `dev` branch should be stable
        pipeline = "exoseq"
        revision = "819cbac792b76cf66c840b567ed0ee9a2f620db7"

        download_obj = DownloadWorkflow(pipeline=pipeline, revision=revision)
        (
            download_obj.pipeline,
            download_obj.wf_revisions,
            download_obj.wf_branches,
        ) = nf_core.utils.get_repo_releases_branches(pipeline, wfs)
        download_obj.get_revision_hash()
        assert download_obj.wf_sha[download_obj.revision[0]] == revision
        assert download_obj.outdir == f"nf-core-exoseq_{revision}"
        assert (
            download_obj.wf_download_url[download_obj.revision[0]]
            == f"https://github.com/nf-core/exoseq/archive/{revision}.zip"
        )

    def test_get_release_hash_short_commit(self):
        wfs = nf_core.pipelines.list.Workflows()
        wfs.get_remote_workflows()
        # Exoseq pipeline is archived, so `dev` branch should be stable
        pipeline = "exoseq"
        revision = "819cbac792b76cf66c840b567ed0ee9a2f620db7"
        short_rev = revision[:7]

        download_obj = DownloadWorkflow(pipeline="exoseq", revision=short_rev)
        (
            download_obj.pipeline,
            download_obj.wf_revisions,
            download_obj.wf_branches,
        ) = nf_core.utils.get_repo_releases_branches(pipeline, wfs)
        download_obj.get_revision_hash()
        print(download_obj)
        assert download_obj.wf_sha[download_obj.revision[0]] == revision
        assert download_obj.outdir == f"nf-core-exoseq_{short_rev}"
        assert (
            download_obj.wf_download_url[download_obj.revision[0]]
            == f"https://github.com/nf-core/exoseq/archive/{revision}.zip"
        )

    def test_get_release_hash_non_existent_release(self):
        wfs = nf_core.pipelines.list.Workflows()
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
        create_obj = nf_core.pipelines.create.create.PipelineCreate(
            "testpipeline",
            "This is a test pipeline",
            "Test McTestFace",
            no_git=True,
            outdir=test_pipeline_dir,
        )
        create_obj.init_pipeline()

        with tempfile.TemporaryDirectory() as test_outdir:
            download_obj = DownloadWorkflow(pipeline="dummy", revision="1.2.0", outdir=test_outdir)
            shutil.copytree(test_pipeline_dir, Path(test_outdir, "workflow"))
            download_obj.download_configs()

            # Test the function
            download_obj.wf_use_local_configs("workflow")
            wf_config = nf_core.utils.fetch_wf_config(Path(test_outdir, "workflow"), cache_config=False)
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
        result = run_cmd("nextflow", f"config -flat {TEST_DATA_DIR}'/mock_config_containers'")
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
        download_obj.find_container_images(str(Path(TEST_DATA_DIR, "mock_module_containers")))

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

        # mock_seqera_container_oras.nf
        assert "oras://community.wave.seqera.io/library/umi-transfer:1.0.0--e5b0c1a65b8173b6" in download_obj.containers
        assert "community.wave.seqera.io/library/umi-transfer:1.0.0--d30e8812ea280fa1" not in download_obj.containers

        # mock_seqera_container_oras_mulled.nf
        assert (
            "oras://community.wave.seqera.io/library/umi-transfer_umicollapse:796a995ff53da9e3"
            in download_obj.containers
        )
        assert (
            "community.wave.seqera.io/library/umi-transfer_umicollapse:3298d4f1b49e33bd" not in download_obj.containers
        )

        # mock_seqera_container_http.nf
        assert (
            "https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/c2/c262fc09eca59edb5a724080eeceb00fb06396f510aefb229c2d2c6897e63975/data"
            in download_obj.containers
        )

        # ToDO: This URI should actually NOT be in there, but prioritize_direct_download() can not handle this case.
        #
        # It works purely by comparing the strings, thus can establish the equivalence of 'https://depot.galaxyproject.org/singularity/umi_tools:1.1.5--py39hf95cd2a_0'
        # and 'biocontainers/umi_tools:1.1.5--py39hf95cd2a_0' because of the identical string 'umi_tools:1.1.5--py39hf95cd2a_0', but has no means to establish that
        # 'https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/c2/c262fc09eca59edb5a724080eeceb00fb06396f510aefb229c2d2c6897e63975/data' and
        # 'community.wave.seqera.io/library/coreutils:9.5--ae99c88a9b28c264' are the equivalent container. It would need to query an API at Seqera for that.

        assert "community.wave.seqera.io/library/coreutils:9.5--ae99c88a9b28c264" in download_obj.containers

    #
    # Test for 'prioritize_direct_download'
    #
    @with_temporary_folder
    def test_prioritize_direct_download(self, tmp_path):
        download_obj = DownloadWorkflow(pipeline="dummy", outdir=tmp_path)

        # tests deduplication and https priority as well as Seqera Container exception

        test_container = [
            "https://depot.galaxyproject.org/singularity/ubuntu:22.04",
            "nf-core/ubuntu:22.04",
            "biocontainers/umi-transfer:1.5.0--h715e4b3_0",
            "https://depot.galaxyproject.org/singularity/umi-transfer:1.5.0--h715e4b3_0",
            "biocontainers/umi-transfer:1.5.0--h715e4b3_0",
            "quay.io/nf-core/sortmerna:4.3.7--6502243397c065ba",
            "nf-core/sortmerna:4.3.7--6502243397c065ba",
            "https://depot.galaxyproject.org/singularity/sortmerna:4.3.7--hdbdd923_1",
            "https://depot.galaxyproject.org/singularity/sortmerna:4.3.7--hdbdd923_0",
            "https://depot.galaxyproject.org/singularity/sortmerna:4.2.0--h9ee0642_1",
            "https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/63/6397750e9730a3fbcc5b4c43f14bd141c64c723fd7dad80e47921a68a7c3cd21/data",
            "https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/c2/c262fc09eca59edb5a724080eeceb00fb06396f510aefb229c2d2c6897e63975/data",
            "https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/c2/c262fc09eca59edb5a724080eeceb00fb06396f510aefb229c2d2c6897e63975/data",
        ]

        result = download_obj.prioritize_direct_download(test_container)

        # Verify that the priority works for regular https downloads (https encountered first)
        assert "https://depot.galaxyproject.org/singularity/ubuntu:22.04" in result
        assert "nf-core/ubuntu:22.04" not in result

        # Verify that the priority works for regular https downloads (https encountered second)
        assert "biocontainers/umi-transfer:1.5.0--h715e4b3_0" not in result
        assert "https://depot.galaxyproject.org/singularity/umi-transfer:1.5.0--h715e4b3_0" in result

        # Verify that the priority works for images with and without explicit registry
        # No priority here, though - the first is retained.
        assert "nf-core/sortmerna:4.3.7--6502243397c065ba" in result
        assert "quay.io/nf-core/sortmerna:4.3.7--6502243397c065ba" not in result

        # Verify that different versions of the same tool and different build numbers are retained
        assert "https://depot.galaxyproject.org/singularity/sortmerna:4.3.7--hdbdd923_1" in result
        assert "https://depot.galaxyproject.org/singularity/sortmerna:4.3.7--hdbdd923_0" in result
        assert "https://depot.galaxyproject.org/singularity/sortmerna:4.2.0--h9ee0642_1" in result

        # Verify that Seqera containers are not deduplicated...
        assert (
            "https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/63/6397750e9730a3fbcc5b4c43f14bd141c64c723fd7dad80e47921a68a7c3cd21/data"
            in result
        )
        assert (
            "https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/c2/c262fc09eca59edb5a724080eeceb00fb06396f510aefb229c2d2c6897e63975/data"
            in result
        )
        # ...but identical ones are.
        assert (
            result.count(
                "https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/c2/c262fc09eca59edb5a724080eeceb00fb06396f510aefb229c2d2c6897e63975/data"
            )
            == 1
        )

    #
    # Test for 'reconcile_seqera_container_uris'
    #
    @with_temporary_folder
    def test_reconcile_seqera_container_uris(self, tmp_path):
        download_obj = DownloadWorkflow(pipeline="dummy", outdir=tmp_path)

        prioritized_container = [
            "oras://community.wave.seqera.io/library/umi-transfer:1.0.0--e5b0c1a65b8173b6",
            "oras://community.wave.seqera.io/library/sylph:0.6.1--b97274cdc1caa649",
        ]

        test_container = [
            "https://depot.galaxyproject.org/singularity/ubuntu:22.04",
            "nf-core/ubuntu:22.04",
            "nf-core/ubuntu:22.04",
            "nf-core/ubuntu:22.04",
            "community.wave.seqera.io/library/umi-transfer:1.5.0--73c1a6b65e5b0b81",
            "community.wave.seqera.io/library/sylph:0.6.1--a21713a57a65a373",
            "biocontainers/sylph:0.6.1--b97274cdc1caa649",
        ]

        # test that the test_container list is returned as it is, if no prioritized_containers are specified
        result_empty = download_obj.reconcile_seqera_container_uris([], test_container)
        assert result_empty == test_container

        result = download_obj.reconcile_seqera_container_uris(prioritized_container, test_container)

        # Verify that unrelated images are retained
        assert "https://depot.galaxyproject.org/singularity/ubuntu:22.04" in result
        assert "nf-core/ubuntu:22.04" in result

        # Verify that the priority works for regular Seqera container (Native Singularity over Docker, but only for Seqera registry)
        assert "oras://community.wave.seqera.io/library/sylph:0.6.1--b97274cdc1caa649" in result
        assert "community.wave.seqera.io/library/sylph:0.6.1--a21713a57a65a373" not in result
        assert "biocontainers/sylph:0.6.1--b97274cdc1caa649" in result

        # Verify that version strings are respected: Version 1.0.0 does not replace version 1.5.0
        assert "oras://community.wave.seqera.io/library/umi-transfer:1.0.0--e5b0c1a65b8173b6" in result
        assert "community.wave.seqera.io/library/umi-transfer:1.5.0--73c1a6b65e5b0b81" in result

        # assert that the deduplication works
        assert test_container.count("nf-core/ubuntu:22.04") == 3
        assert result.count("nf-core/ubuntu:22.04") == 1

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
        singularity_fetcher = SingularityFetcher([], [], mock_rich_progress)

        # Test successful pull
        singularity_fetcher.pull_image("hello-world", f"{tmp_dir}/hello-world.sif", "docker.io")

        # Pull again, but now the image already exists
        with pytest.raises(ContainerError.ImageExistsError):
            singularity_fetcher.pull_image("hello-world", f"{tmp_dir}/hello-world.sif", "docker.io")

        # Test successful pull with absolute URI (use tiny 3.5MB test container from the "Kogia" project: https://github.com/bschiffthaler/kogia)
        singularity_fetcher.pull_image("docker.io/bschiffthaler/sed", f"{tmp_dir}/sed.sif", "docker.io")

        # Test successful pull with absolute oras:// URI
        singularity_fetcher.pull_image(
            "oras://community.wave.seqera.io/library/umi-transfer:1.0.0--e5b0c1a65b8173b6",
            f"{tmp_dir}/umi-transfer-oras.sif",
            "docker.io",
        )

        # try pulling Docker container image with oras://
        with pytest.raises(ContainerError.NoSingularityContainerError):
            singularity_fetcher.pull_image(
                "oras://ghcr.io/matthiaszepper/umi-transfer:dev",
                f"{tmp_dir}/umi-transfer-oras_impostor.sif",
                "docker.io",
            )

        # try to pull from non-existing registry (Name change hello-world_new.sif is needed, otherwise ImageExistsError is raised before attempting to pull.)
        with pytest.raises(ContainerError.RegistryNotFoundError):
            singularity_fetcher.pull_image(
                "hello-world",
                f"{tmp_dir}/break_the_registry_test.sif",
                "register-this-domain-to-break-the-test.io",
            )

        # test Image not found for several registries
        with pytest.raises(ContainerError.ImageNotFoundError):
            singularity_fetcher.pull_image("a-container", f"{tmp_dir}/acontainer.sif", "quay.io")

        with pytest.raises(ContainerError.ImageNotFoundError):
            singularity_fetcher.pull_image("a-container", f"{tmp_dir}/acontainer.sif", "docker.io")

        with pytest.raises(ContainerError.ImageNotFoundError):
            singularity_fetcher.pull_image("a-container", f"{tmp_dir}/acontainer.sif", "ghcr.io")

        # test Image not found for absolute URI.
        with pytest.raises(ContainerError.ImageNotFoundError):
            singularity_fetcher.pull_image(
                "docker.io/bschiffthaler/nothingtopullhere",
                f"{tmp_dir}/nothingtopullhere.sif",
                "docker.io",
            )

        # Traffic from Github Actions to GitHub's Container Registry is unlimited, so no harm should be done here.
        with pytest.raises(ContainerError.InvalidTagError):
            singularity_fetcher.pull_image(
                "ewels/multiqc:go-rewrite",
                f"{tmp_dir}/multiqc-go.sif",
                "ghcr.io",
            )

    @pytest.mark.skipif(
        shutil.which("singularity") is None,
        reason="Can't test what Singularity does if it's not installed.",
    )
    @with_temporary_folder
    @mock.patch("rich.progress.Progress.add_task")
    def test_singularity_pull_image_successfully(self, tmp_dir, mock_rich_progress):
        singularity_fetcher = SingularityFetcher([], [], mock_rich_progress)
        singularity_fetcher.pull_image("hello-world", f"{tmp_dir}/yet-another-hello-world.sif", "docker.io")

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

    #
    # Tests for 'singularity.symlink_registries' function
    #

    # Simple file name with no registry in it
    @with_temporary_folder
    @mock.patch("os.makedirs")
    @mock.patch("os.symlink")
    @mock.patch("os.open")
    @mock.patch("os.close")
    @mock.patch("os.path.basename")
    @mock.patch("os.path.dirname")
    def test_symlink_singularity_images(
        self,
        tmp_path,
        mock_dirname,
        mock_basename,
        mock_close,
        mock_open,
        mock_symlink,
        mock_makedirs,
    ):
        # Setup
        mock_dirname.return_value = f"{tmp_path}/path/to"
        mock_basename.return_value = "singularity-image.img"
        mock_open.return_value = 12  # file descriptor
        mock_close.return_value = 12  # file descriptor

        registries = [
            "quay.io",
            "community-cr-prod.seqera.io/docker/registry/v2",
            "depot.galaxyproject.org/singularity",
        ]

        symlink_registries(f"{tmp_path}/path/to/singularity-image.img", registries)

        # Check that os.makedirs was called with the correct arguments
        mock_makedirs.assert_any_call(f"{tmp_path}/path/to", exist_ok=True)

        # Check that os.open was called with the correct arguments
        mock_open.assert_any_call(f"{tmp_path}/path/to", os.O_RDONLY)

        # Check that os.symlink was called with the correct arguments
        expected_calls = [
            mock.call(
                "./singularity-image.img",
                "./quay.io-singularity-image.img",
                dir_fd=12,
            ),
            mock.call(
                "./singularity-image.img",
                "./community-cr-prod.seqera.io-docker-registry-v2-singularity-image.img",
                dir_fd=12,
            ),
            mock.call(
                "./singularity-image.img",
                "./depot.galaxyproject.org-singularity-singularity-image.img",
                dir_fd=12,
            ),
        ]
        mock_symlink.assert_has_calls(expected_calls, any_order=True)

    # File name with registry in it
    @with_temporary_folder
    @mock.patch("os.makedirs")
    @mock.patch("os.symlink")
    @mock.patch("os.open")
    @mock.patch("os.close")
    @mock.patch("re.sub")
    @mock.patch("os.path.basename")
    @mock.patch("os.path.dirname")
    def test_symlink_singularity_symlink_registries(
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

        # Call the method with registry name included - should not happen, but preserve it then.
        registries = [
            "quay.io",  # Same as in the filename
            "community-cr-prod.seqera.io/docker/registry/v2",
        ]
        symlink_registries(f"{tmp_path}/path/to/quay.io-singularity-image.img", registries)

        # Check that os.makedirs was called with the correct arguments
        mock_makedirs.assert_called_once_with(f"{tmp_path}/path/to", exist_ok=True)

        # Check that os.symlink was called with the correct arguments
        # assert_called_once_with also tells us that there was no attempt to
        # - symlink to itself
        # - symlink to the same registry
        mock_symlink.assert_called_once_with(
            "./quay.io-singularity-image.img",
            "./community-cr-prod.seqera.io-docker-registry-v2-singularity-image.img",  # "quay.io-" has been trimmed
            dir_fd=12,
        )

        # Normally it would be called for each registry, but since quay.io is part of the name, it
        # will only be called once, as no symlink to itself must be created.
        mock_open.assert_called_once_with(f"{tmp_path}/path/to", os.O_RDONLY)

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
        shutil.which("singularity") is not None,
        reason="Can't test how the code behaves when singularity is not installed if it is.",
    )
    @with_temporary_folder
    @mock.patch("rich.progress.Progress.add_task")
    def test_singularity_pull_image_singularity_not_installed(self, tmp_dir, mock_rich_progress):
        singularity_fetcher = SingularityFetcher([], [], mock_rich_progress)
        with pytest.raises(OSError):
            singularity_fetcher.pull_image("a-container", f"{tmp_dir}/anothercontainer.sif", "quay.io")

    #
    # Test for 'singularity.get_container_filename' function
    #
    def test_singularity_get_container_filename(self):
        registries = [
            "docker.io",
            "quay.io",
            "depot.galaxyproject.org/singularity",
            "community.wave.seqera.io/library",
            "community-cr-prod.seqera.io/docker/registry/v2",
        ]

        # Test --- galaxy URL but no registry given #
        result = get_container_filename(
            "https://depot.galaxyproject.org/singularity/bbmap:38.93--he522d1c_0",
            [],
        )
        assert result == "depot.galaxyproject.org-singularity-bbmap-38.93--he522d1c_0.img"

        # Test --- galaxy URL #
        result = get_container_filename(
            "https://depot.galaxyproject.org/singularity/bbmap:38.93--he522d1c_0",
            registries,
        )
        assert result == "bbmap-38.93--he522d1c_0.img"

        # Test --- mulled containers #
        result = get_container_filename(
            "quay.io/biocontainers/mulled-v2-1fa26d1ce03c295fe2fdcf85831a92fbcbd7e8c2:59cdd445419f14abac76b31dd0d71217994cbcc9-0",
            registries,
        )
        assert (
            result
            == "biocontainers-mulled-v2-1fa26d1ce03c295fe2fdcf85831a92fbcbd7e8c2-59cdd445419f14abac76b31dd0d71217994cbcc9-0.img"
        )

        # Test --- Docker containers without registry #
        result = get_container_filename("nf-core/ubuntu:20.04", registries)
        assert result == "nf-core-ubuntu-20.04.img"

        # Test --- Docker container with explicit registry -> should be trimmed #
        result = get_container_filename("docker.io/nf-core/ubuntu:20.04", registries)
        assert result == "nf-core-ubuntu-20.04.img"

        # Test --- Docker container with explicit registry not in registry list -> can't be trimmed
        result = get_container_filename("mirage-the-imaginative-registry.io/nf-core/ubuntu:20.04", registries)
        assert result == "mirage-the-imaginative-registry.io-nf-core-ubuntu-20.04.img"

        # Test --- Seqera Docker containers: Trimmed, because it is hard-coded in the registry set.
        result = get_container_filename("community.wave.seqera.io/library/coreutils:9.5--ae99c88a9b28c264", registries)
        assert result == "coreutils-9.5--ae99c88a9b28c264.img"

        # Test --- Seqera Singularity containers: Trimmed, because it is hard-coded in the registry set.
        result = get_container_filename(
            "https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/c2/c262fc09eca59edb5a724080eeceb00fb06396f510aefb229c2d2c6897e63975/data",
            registries,
        )
        assert result == "blobs-sha256-c2-c262fc09eca59edb5a724080eeceb00fb06396f510aefb229c2d2c6897e63975-data.img"

        # Test --- Seqera Oras containers: Trimmed, because it is hard-coded in the registry set.
        result = get_container_filename(
            "oras://community.wave.seqera.io/library/umi-transfer:1.0.0--e5b0c1a65b8173b6",
            registries,
        )
        assert result == "umi-transfer-1.0.0--e5b0c1a65b8173b6.img"

        # Test --- SIF Singularity container with explicit registry -> should be trimmed #
        result = get_container_filename(
            "docker.io-hashicorp-vault-1.16-sha256:e139ff28c23e1f22a6e325696318141259b177097d8e238a3a4c5b84862fadd8.sif",
            registries,
        )
        assert (
            result == "hashicorp-vault-1.16-sha256-e139ff28c23e1f22a6e325696318141259b177097d8e238a3a4c5b84862fadd8.sif"
        )

        # Test --- SIF Singularity container without registry #
        result = get_container_filename(
            "singularity-hpc/shpc/tests/testdata/salad_latest.sif",
            registries,
        )
        assert result == "singularity-hpc-shpc-tests-testdata-salad_latest.sif"

        # Test --- Singularity container from a Singularity registry (and version tag) #
        result = get_container_filename(
            "library://pditommaso/foo/bar.sif:latest",
            registries,
        )
        assert result == "pditommaso-foo-bar-latest.sif"

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
            container_cache_index=str(Path(TEST_DATA_DIR, "testdata_remote_containers.txt")),
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
    @mock.patch("nf_core.pipelines.downloads.singularity.SingularityFetcher.pull_image")
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
    @mock.patch("nf_core.pipelines.download.DownloadWorkflow.get_singularity_images")
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

        wfs = nf_core.pipelines.list.Workflows()
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
        assert isinstance(download_obj.outdir, str)
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

        # clean-up
        # remove "nf-core-rnaseq*" directories
        for path in Path().cwd().glob("nf-core-rnaseq*"):
            shutil.rmtree(path)

    #
    # Brief test adding a single custom tag to Seqera Platform download
    #
    @mock.patch("nf_core.pipelines.download.DownloadWorkflow.get_singularity_images")
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

        # clean-up
        # remove "nf-core-rnaseq*" directories
        for path in Path().cwd().glob("nf-core-rnaseq*"):
            shutil.rmtree(path)

    #
    # Test adding custom tags to Seqera Platform download (full test)
    #
    @mock.patch("nf_core.pipelines.download.DownloadWorkflow.get_singularity_images")
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

            wfs = nf_core.pipelines.list.Workflows()
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

            # clean-up
            # remove "nf-core-rnaseq*" directories
            for path in Path().cwd().glob("nf-core-rnaseq*"):
                shutil.rmtree(path)
