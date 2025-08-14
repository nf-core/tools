import logging
import os
import subprocess
import unittest
from pathlib import Path
from unittest import mock

import pytest
import requests
import rich.progress_bar
import rich.table
import rich.text

from nf_core.pipelines.download.container_fetcher import ContainerProgress
from nf_core.pipelines.download.docker import (
    DockerProgress,
)
from nf_core.pipelines.download.singularity import (
    FileDownloader,
    SingularityProgress,
)
from nf_core.pipelines.download.utils import (
    DownloadError,
    intermediate_file,
)

from ..utils import with_temporary_folder


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
                subprocess.cggheck_call(["ls", "/dummy"])

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
            assert table.columns[4]._cells[0] == "[green]11/42 tasks completed"

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
