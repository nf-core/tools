"""Tests for the download subcommand of nf-core tools"""

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pytest
import requests
import rich.progress_bar
import rich.table
import rich.text

import nf_core.pipelines.create.create
import nf_core.pipelines.download
import nf_core.pipelines.list
import nf_core.utils
from nf_core.pipelines.download import DownloadWorkflow
from nf_core.pipelines.download.container_fetcher import ContainerProgress
from nf_core.pipelines.download.docker import DockerProgress
from nf_core.pipelines.download.singularity import (
    FileDownloader,
    SingularityError,
    SingularityFetcher,
    SingularityProgress,
)
from nf_core.pipelines.download.utils import (
    DownloadError,
    intermediate_file,
)
from nf_core.pipelines.download.workflow_repo import WorkflowRepo
from nf_core.synced_repo import SyncedRepo
from nf_core.utils import (
    NF_INSPECT_MIN_NF_VERSION,
    check_nextflow_version,
)

from ..utils import TEST_DATA_DIR, with_temporary_folder


class DownloadUtilsTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def use_caplog(self, caplog):
        self._caplog = caplog

    #
    # Test for 'utils.intermediate_file'
    #
    @with_temporary_folder
    def test_intermediate_file(self, outdir):
        outdir = Path(outdir)
        # Code that doesn't fail. The file shall exist

        # Directly write to the file, as in download_image
        output_path = outdir / "testfile1"
        with intermediate_file(output_path) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(b"Hello, World!")

        assert output_path.exists()
        assert os.path.getsize(output_path) == 13
        assert not tmp_path.exists()

        # Run an external command as in pull_image
        output_path = outdir / "testfile2"
        with intermediate_file(output_path) as tmp:
            tmp_path = Path(tmp.name)
            subprocess.check_call([f"echo 'Hello, World!' > {tmp_path}"], shell=True)

        assert (output_path).exists()
        assert os.path.getsize(output_path) == 14  # Extra \n !
        assert not (tmp_path).exists()

        # Code that fails. The file shall not exist

        # Directly write to the file and raise an exception
        output_path = outdir / "testfile3"
        with pytest.raises(ValueError):
            with intermediate_file(output_path) as tmp:
                tmp_path = Path(tmp.name)
                tmp.write(b"Hello, World!")
                raise ValueError("This is a test error")

        assert not (output_path).exists()
        assert not (tmp_path).exists()

        # Run an external command and raise an exception
        output_path = outdir / "testfile4"
        with pytest.raises(subprocess.CalledProcessError):
            with intermediate_file(output_path) as tmp:
                tmp_path = Path(tmp.name)
                subprocess.check_call([f"echo 'Hello, World!' > {tmp_path}"], shell=True)
                subprocess.check_call(["ls", "/dummy"])

        assert not (output_path).exists()
        assert not (tmp_path).exists()

        # Test for invalid output paths
        with pytest.raises(DownloadError):
            with intermediate_file(outdir) as tmp:
                pass

        output_path = outdir / "testfile5"
        os.symlink("/dummy", output_path)
        with pytest.raises(DownloadError):
            with intermediate_file(output_path) as tmp:
                pass

    #
    # Test for 'utils.DownloadProgress.add/update_main_task'
    #
    def test_download_progress_main_task(self):
        with ContainerProgress() as progress:
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
        with ContainerProgress() as progress:
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
        # Test the "summary" progress type
        with ContainerProgress() as progress:
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

        #
        # Test the SingularityProgress subclass
        #

        # Test the "singularity_pull" progress type
        with SingularityProgress() as progress:
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

        # Test the "download" progress type
        with SingularityProgress() as progress:
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
        # Test the DockerProgress subclass
        #
        with DockerProgress() as progress:
            assert progress.tasks == []
            progress.add_task(
                "Task 1", progress_type="docker", total=2, completed=1, current_log="example log", status="Pulling"
            )
            assert len(progress.tasks) == 1

            renderable = progress.get_renderable()
            assert isinstance(renderable, rich.console.Group), type(renderable)

            assert len(renderable.renderables) == 1
            table = renderable.renderables[0]
            assert isinstance(table, rich.table.Table)

            assert isinstance(table.columns[0]._cells[0], str)
            assert table.columns[0]._cells[0] == "[magenta]Task 1"
            assert isinstance(table.columns[2]._cells[0], str)
            assert table.columns[2]._cells[0] == "([blue]Pulling)"

    #
    # Test for 'singularity.FileDownloader.download_file'
    #
    @with_temporary_folder
    def test_file_download(self, outdir):
        outdir = Path(outdir)
        with ContainerProgress() as progress:
            downloader = FileDownloader(progress)

            # Activate the caplog: all download attempts must be logged (even failed ones)
            self._caplog.clear()
            with self._caplog.at_level(logging.DEBUG):
                # No task initially
                assert progress.tasks == []
                assert progress._task_index == 0

                # Download a file
                src_url = "https://github.com/nf-core/test-datasets/raw/refs/heads/modules/data/genomics/sarscov2/genome/genome.fasta.fai"
                output_path = outdir / Path(src_url).name
                downloader.download_file(src_url, output_path)
                assert (output_path).exists()
                assert os.path.getsize(output_path) == 27
                assert (
                    "nf_core.pipelines.download.singularity",
                    logging.DEBUG,
                    f"Downloading '{src_url}' to '{output_path}'",
                ) in self._caplog.record_tuples

                # A task was added but is now gone
                assert progress._task_index == 1
                assert progress.tasks == []

                # No content at the URL
                src_url = "http://www.google.com/generate_204"
                output_path = outdir / Path(src_url).name
                with pytest.raises(DownloadError):
                    downloader.download_file(src_url, output_path)
                assert not (output_path).exists()
                assert (
                    "nf_core.pipelines.download.singularity",
                    logging.DEBUG,
                    f"Downloading '{src_url}' to '{output_path}'",
                ) in self._caplog.record_tuples

                # A task was added but is now gone
                assert progress._task_index == 2
                assert progress.tasks == []

                # Invalid URL (schema)
                src_url = "dummy://github.com/nf-core/test-datasets/raw/refs/heads/modules/data/genomics/sarscov2/genome/genome.fasta.fax"
                output_path = outdir / Path(src_url).name
                with pytest.raises(requests.exceptions.InvalidSchema):
                    downloader.download_file(src_url, output_path)
                assert not (output_path).exists()
                assert (
                    "nf_core.pipelines.download.singularity",
                    logging.DEBUG,
                    f"Downloading '{src_url}' to '{output_path}'",
                ) in self._caplog.record_tuples

                # A task was added but is now gone
                assert progress._task_index == 3
                assert progress.tasks == []

            # Fire in the hole ! The download will be aborted and no output file will be created
            src_url = "https://github.com/nf-core/test-datasets/raw/refs/heads/modules/data/genomics/sarscov2/genome/genome.fasta.fai"
            output_path = outdir / Path(src_url).name
            os.unlink(output_path)
            downloader.kill_with_fire = True
            with pytest.raises(KeyboardInterrupt):
                downloader.download_file(src_url, output_path)
            assert not (output_path).exists()

    #
    # Test for 'singularity.FileDownloader.download_files_in_parallel'
    #
    @with_temporary_folder
    def test_parallel_downloads(self, outdir):
        outdir = Path(outdir)

        # Prepare the download paths
        def make_tuple(url):
            return (url, (outdir / Path(url).name))

        download_fai = make_tuple(
            "https://github.com/nf-core/test-datasets/raw/refs/heads/modules/data/genomics/sarscov2/genome/genome.fasta.fai"
        )
        download_dict = make_tuple(
            "https://github.com/nf-core/test-datasets/raw/refs/heads/modules/data/genomics/sarscov2/genome/genome.dict"
        )
        download_204 = make_tuple("http://www.google.com/generate_204")
        download_schema = make_tuple(
            "dummy://github.com/nf-core/test-datasets/raw/refs/heads/modules/data/genomics/sarscov2/genome/genome.fasta.fax"
        )

        with ContainerProgress() as progress:
            downloader = FileDownloader(progress)

            # Download two files
            assert downloader.kill_with_fire is False
            downloads = [download_fai, download_dict]
            downloaded_files = downloader.download_files_in_parallel(downloads, parallel_downloads=1)
            assert len(downloaded_files) == 2
            assert downloaded_files == downloads
            assert (download_fai[1]).exists()
            assert (download_dict[1]).exists()
            assert downloader.kill_with_fire is False
            (download_fai[1]).unlink()
            (download_dict[1]).unlink()

            # This time, the second file will raise an exception
            assert downloader.kill_with_fire is False
            downloads = [download_fai, download_204]
            with pytest.raises(DownloadError):
                downloader.download_files_in_parallel(downloads, parallel_downloads=1)
            assert downloader.kill_with_fire is False
            assert (download_fai[1]).exists()
            assert not (download_204[1]).exists()
            (download_fai[1]).unlink()

            # Now we swap the two files. The first one will raise an exception but the
            # second one will still be downloaded because only KeyboardInterrupt can
            # stop everything altogether.
            assert downloader.kill_with_fire is False
            downloads = [download_204, download_fai]
            with pytest.raises(DownloadError):
                downloader.download_files_in_parallel(downloads, parallel_downloads=1)
            assert downloader.kill_with_fire is False
            assert (download_fai[1]).exists()
            assert not (download_204[1]).exists()
            (download_fai[1]).unlink()

            # We check that there's the same behaviour with `requests` errors.
            assert downloader.kill_with_fire is False
            downloads = [download_schema, download_fai]
            with pytest.raises(DownloadError):
                downloader.download_files_in_parallel(downloads, parallel_downloads=1)
            assert downloader.kill_with_fire is False
            assert (download_fai[1]).exists()
            assert not (download_schema[1]).exists()
            (download_fai[1]).unlink()

            # Now we check the callback method
            callbacks = []

            def callback(*args):
                callbacks.append(args)

            # We check the same scenarios as above
            callbacks = []
            downloads = [download_fai, download_dict]
            downloader.download_files_in_parallel(downloads, parallel_downloads=1, callback=callback)
            assert len(callbacks) == 2
            assert callbacks == [
                (download_fai, FileDownloader.Status.DONE),
                (download_dict, FileDownloader.Status.DONE),
            ]

            callbacks = []
            downloads = [download_fai, download_204]
            with pytest.raises(DownloadError):
                downloader.download_files_in_parallel(downloads, parallel_downloads=1, callback=callback)
            assert len(callbacks) == 2
            assert callbacks == [
                (download_fai, FileDownloader.Status.DONE),
                (download_204, FileDownloader.Status.ERROR),
            ]

            callbacks = []
            downloads = [download_204, download_fai]
            with pytest.raises(DownloadError):
                downloader.download_files_in_parallel(downloads, parallel_downloads=1, callback=callback)
            assert len(callbacks) == 2
            assert callbacks == [
                (download_204, FileDownloader.Status.ERROR),
                (download_fai, FileDownloader.Status.DONE),
            ]

            callbacks = []
            downloads = [download_schema, download_fai]
            with pytest.raises(DownloadError):
                downloader.download_files_in_parallel(downloads, parallel_downloads=1, callback=callback)
            assert len(callbacks) == 2
            assert callbacks == [
                (download_schema, FileDownloader.Status.ERROR),
                (download_fai, FileDownloader.Status.DONE),
            ]

            # Finally, we check how the function behaves when a KeyboardInterrupt is raised
            with mock.patch("concurrent.futures.wait", side_effect=KeyboardInterrupt):
                callbacks = []
                downloads = [download_fai, download_204, download_dict]
                with pytest.raises(KeyboardInterrupt):
                    downloader.download_files_in_parallel(downloads, parallel_downloads=1, callback=callback)
                assert len(callbacks) == 3
                # Note: whn the KeyboardInterrupt is raised, download_204 and download_dict are not yet started.
                # They are therefore cancelled and pushed to the callback list immediately. download_fai is last
                # because it is running and can't be cancelled.
                assert callbacks == [
                    (download_204, FileDownloader.Status.CANCELLED),
                    (download_dict, FileDownloader.Status.CANCELLED),
                    (download_fai, FileDownloader.Status.ERROR),
                ]


class DownloadTest(unittest.TestCase):
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
        assert download_obj.outdir == Path("nf-core-methylseq_1.6")
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
        assert download_obj.outdir == Path("nf-core-exoseq_dev")
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
        assert download_obj.outdir == Path(f"nf-core-exoseq_{revision}")
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
        assert download_obj.outdir == Path(f"nf-core-exoseq_{short_rev}")
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
        outdir = Path(outdir)
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

        assert ((outdir / rev) / "main.nf").exists()

    #
    # Tests for 'download_configs'
    #
    @with_temporary_folder
    def test_download_configs(self, outdir):
        outdir = Path(outdir)
        download_obj = DownloadWorkflow(pipeline="nf-core/methylseq", revision="1.6")
        download_obj.outdir = outdir
        download_obj.download_configs()
        assert (outdir / "configs") / "nfcore_custom.config"

    #
    # Tests for 'wf_use_local_configs'
    #
    @with_temporary_folder
    def test_wf_use_local_configs(self, tmp_path):
        tmp_path = Path(tmp_path)
        # Get a workflow and configs
        test_pipeline_dir = tmp_path / "nf-core-testpipeline"
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
    # Test that `find_container_images` (uses `nextflow inspect`) and `find_container_images_legacy`
    # produces the same results
    #
    @pytest.mark.skipif(
        shutil.which("nextflow") is None or not check_nextflow_version(NF_INSPECT_MIN_NF_VERSION),
        reason="Can't run test that requires nextflow to run if not installed.",
    )
    @with_temporary_folder
    @mock.patch("nf_core.utils.fetch_wf_config")
    def test_containers_pipeline_singularity(self, tmp_path, mock_fetch_wf_config):
        tmp_path = Path(tmp_path)
        assert check_nextflow_version(NF_INSPECT_MIN_NF_VERSION) is True

        # Set up test
        container_system = "singularity"
        mock_pipeline_dir = TEST_DATA_DIR / "mock_pipeline_containers"
        refererence_json_dir = mock_pipeline_dir / "per_profile_output"
        # First check that `-profile singularity` produces the same output as the reference
        download_obj = DownloadWorkflow(pipeline="dummy", outdir=tmp_path, container_system=container_system)
        mock_fetch_wf_config.return_value = {}

        # Run get containers with `nextflow inspect`
        entrypoint = "main_passing_test.nf"
        download_obj.find_container_images(mock_pipeline_dir, entrypoint=entrypoint)

        # Store the containers found by the new method
        found_containers = set(download_obj.containers)

        # Load the reference containers
        with open(refererence_json_dir / f"{container_system}_containers.json") as fh:
            ref_containers = json.load(fh)
            ref_container_strs = set(ref_containers.values())

        # Now check that they contain the same containers
        assert found_containers == ref_container_strs, (
            f"Containers found in pipeline by `nextflow inspect`: {found_containers}\n"
            f"Containers that should've been found: {ref_container_strs}"
        )

    #
    # Test that `find_container_images` (uses `nextflow inspect`) and `find_container_images_legacy`
    # produces the same results
    #
    @pytest.mark.skipif(
        shutil.which("nextflow") is None or not check_nextflow_version(NF_INSPECT_MIN_NF_VERSION),
        reason=f"Can't run test that requires Nextflow >= {NF_INSPECT_MIN_NF_VERSION} to run if not installed.",
    )
    @with_temporary_folder
    @mock.patch("nf_core.utils.fetch_wf_config")
    def test_containers_pipeline_docker(self, tmp_path, mock_fetch_wf_config):
        tmp_path = Path(tmp_path)
        assert check_nextflow_version(NF_INSPECT_MIN_NF_VERSION) is True

        # Set up test
        container_system = "docker"
        mock_pipeline_dir = TEST_DATA_DIR / "mock_pipeline_containers"
        refererence_json_dir = mock_pipeline_dir / "per_profile_output"
        # First check that `-profile singularity` produces the same output as the reference
        download_obj = DownloadWorkflow(pipeline="dummy", outdir=tmp_path, container_system=container_system)
        mock_fetch_wf_config.return_value = {}

        # Run get containers with `nextflow inspect`
        entrypoint = "main_passing_test.nf"
        download_obj.find_container_images(mock_pipeline_dir, entrypoint=entrypoint)

        # Store the containers found by the new method
        found_containers = set(download_obj.containers)

        # Load the reference containers
        with open(refererence_json_dir / f"{container_system}_containers.json") as fh:
            ref_containers = json.load(fh)
            ref_container_strs = set(ref_containers.values())

        # Now check that they contain the same containers
        assert found_containers == ref_container_strs, (
            f"Containers found in pipeline by `nextflow inspect`: {found_containers}\n"
            f"Containers that should've been found: {ref_container_strs}"
        )

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
        singularity_fetcher = SingularityFetcher([], [], "none", None)
        singularity_fetcher.progress = mock_progress()
        # Test successful pull
        singularity_fetcher.pull_image("hello-world", f"{tmp_dir}/hello-world.sif", "docker.io")

        # Pull again, but now the image already exists
        with pytest.raises(SingularityError.ImageExistsError):
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
        with pytest.raises(SingularityError.NoSingularityContainerError):
            singularity_fetcher.pull_image(
                "oras://ghcr.io/matthiaszepper/umi-transfer:dev",
                f"{tmp_dir}/umi-transfer-oras_impostor.sif",
                "docker.io",
            )

        # try to pull from non-existing registry (Name change hello-world_new.sif is needed, otherwise ImageExistsError is raised before attempting to pull.)
        with pytest.raises(SingularityError.RegistryNotFoundError):
            singularity_fetcher.pull_image(
                "hello-world",
                f"{tmp_dir}/break_the_registry_test.sif",
                "register-this-domain-to-break-the-test.io",
            )

        # test Image not found for several registries
        with pytest.raises(SingularityError.ImageNotFoundError):
            singularity_fetcher.pull_image("a-container", f"{tmp_dir}/acontainer.sif", "quay.io")

        with pytest.raises(SingularityError.ImageNotFoundError):
            singularity_fetcher.pull_image("a-container", f"{tmp_dir}/acontainer.sif", "docker.io")

        with pytest.raises(SingularityError.ImageNotFoundError):
            singularity_fetcher.pull_image("a-container", f"{tmp_dir}/acontainer.sif", "ghcr.io")

        # test Image not found for absolute URI.
        with pytest.raises(SingularityError.ImageNotFoundError):
            singularity_fetcher.pull_image(
                "docker.io/bschiffthaler/nothingtopullhere",
                f"{tmp_dir}/nothingtopullhere.sif",
                "docker.io",
            )

        # Traffic from Github Actions to GitHub's Container Registry is unlimited, so no harm should be done here.
        with pytest.raises(SingularityError.InvalidTagError):
            singularity_fetcher.pull_image(
                "ewels/multiqc:go-rewrite",
                f"{tmp_dir}/multiqc-go.sif",
                "ghcr.io",
            )

    @pytest.mark.skipif(
        shutil.which("singularity") is None and shutil.which("apptainer") is None,
        reason="Can't test what Singularity does if it's not installed.",
    )
    @with_temporary_folder
    @mock.patch("nf_core.pipelines.download.singularity.SingularityProgress")
    def test_singularity_pull_image_successfully(self, tmp_dir, mock_progress):
        tmp_dir = Path(tmp_dir)
        singularity_fetcher = SingularityFetcher([], [], "none", None)
        singularity_fetcher.progress = mock_progress()
        singularity_fetcher.pull_image("hello-world", f"{tmp_dir}/yet-another-hello-world.sif", "docker.io")

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
            container_library=download_obj.container_library,
            registry_set=download_obj.registry_set,
            container_cache_utilisation="none",
            container_cache_index=None,
        )
        singularity_fetcher.fetch_containers(
            download_obj.containers,
            download_obj.outdir,
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
            fetcher = SingularityFetcher([], registries, "none", None)

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
            fetcher = SingularityFetcher([], registries, "none", None)
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
    # Test for gather_registries'
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
        with pytest.raises(OSError):
            SingularityFetcher([], [], "none", None)

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

        fetcher = SingularityFetcher([], registries, "none", None)
        print(fetcher.registry_set)
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

    #
    # Tests for the main entry method 'download_workflow'
    #

    # We do not want to download all containers, so we mock the download by just touching the singularity files
    def mock_download_file(self, remote_path: str, output_path: str):
        Path(output_path).touch()  # Create an empty file at the output path

    @with_temporary_folder
    @mock.patch(
        "nf_core.pipelines.download.singularity.SingularityFetcher.check_and_set_implementation"
    )  # This is to make sure that we do not check for Singularity/Apptainer installation
    @mock.patch.object(nf_core.pipelines.download.singularity.FileDownloader, "download_file", new=mock_download_file)
    def test_download_workflow_with_success(self, tmp_dir, mock_check_and_set_implementation):
        tmp_dir = Path(tmp_dir)
        os.environ["NXF_SINGULARITY_CACHEDIR"] = str(tmp_dir / "foo")

        download_obj = DownloadWorkflow(
            pipeline="nf-core/bamtofastq",
            outdir=tmp_dir / "new",
            container_system="singularity",
            revision="2.2.0",
            compress_type="none",
            container_cache_utilisation="copy",
            parallel=1,
        )

        download_obj.include_configs = True  # suppress prompt, because stderr.is_interactive doesn't.
        download_obj.download_workflow()

    #
    # Test Download for Seqera Platform
    #
    @with_temporary_folder
    @mock.patch(
        "nf_core.pipelines.download.singularity.SingularityFetcher.check_and_set_implementation"
    )  # This is to make sure that we do not check for Singularity/Apptainer installation
    @mock.patch("nf_core.pipelines.download.singularity.SingularityFetcher.fetch_containers")
    def test_download_workflow_for_platform(
        self,
        tmp_dir,
        mock_fetch_containers,
        mock_check_and_set_implementation,
    ):
        tmp_dir = Path(tmp_dir)
        download_obj = DownloadWorkflow(
            pipeline="nf-core/rnaseq",
            revision=("3.19.0", "3.17.0"),
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
        assert isinstance(download_obj.outdir, Path)
        assert bool(re.search(r"nf-core-rnaseq_\d{4}-\d{2}-\d{1,2}_\d{1,2}-\d{1,2}", str(download_obj.outdir), re.S))

        download_obj.output_filename = download_obj.outdir.with_suffix(".git")
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

        # download_obj.download_workflow_platform(location=tmp_dir) will run `nextflow inspect` for each revision
        # This means that the containers in download_obj.containers are the containers the last specified revision i.e. 3.17
        assert isinstance(download_obj.containers, list) and len(download_obj.containers) == 39
        assert (
            "https://depot.galaxyproject.org/singularity/bbmap:39.10--h92535d8_0" in download_obj.containers
        )  # direct definition

        # clean-up
        # remove "nf-core-rnaseq*" directories
        for path in Path().cwd().glob("nf-core-rnaseq*"):
            shutil.rmtree(path)

    #
    # Brief test adding a single custom tag to Seqera Platform download
    #
    @mock.patch("nf_core.pipelines.download.singularity.SingularityFetcher.fetch_containers")
    @with_temporary_folder
    def test_download_workflow_for_platform_with_one_custom_tag(self, _, tmp_dir):
        tmp_dir = Path(tmp_dir)
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
    @mock.patch("nf_core.pipelines.download.singularity.SingularityFetcher.fetch_containers")
    @with_temporary_folder
    def test_download_workflow_for_platform_with_custom_tags(self, _, tmp_dir):
        tmp_dir = Path(tmp_dir)
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
