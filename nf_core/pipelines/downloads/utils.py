import concurrent.futures
import contextlib
import io
import logging
import os
import tempfile
from typing import Generator, Iterable, Tuple

import requests
import requests_cache
import rich.progress
import rich.table

log = logging.getLogger(__name__)


class DownloadError(RuntimeError):
    """A custom exception that is raised when nf-core pipelines download encounters a problem that we already took into consideration.
    In this case, we do not want to print the traceback, but give the user some concise, helpful feedback instead.
    """


@contextlib.contextmanager
def intermediate_file(output_path: str) -> Generator[tempfile._TemporaryFileWrapper, None, None]:
    """Context manager to help ensure the output file is either complete or non-existent.
    It does that by creating a temporary file in the same directory as the output file,
    letting the caller write to it, and then moving it to the final location.
    If an exception is raised, the temporary file is deleted and the output file is not touched.
    """
    if os.path.isdir(output_path):
        raise DownloadError(f"Output path '{output_path}' is a directory")
    if os.path.islink(output_path):
        raise DownloadError(f"Output path '{output_path}' is a symbolic link")

    tmp = tempfile.NamedTemporaryFile(dir=os.path.dirname(output_path), delete=False)
    try:
        yield tmp
        tmp.close()
        os.rename(tmp.name, output_path)
    except:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        raise


class DownloadProgress(rich.progress.Progress):
    """Custom Progress bar class, allowing us to have two progress
    bars with different columns / layouts.
    Also provide helper functions to control the top-level task.
    """

    def get_renderables(self) -> Generator[rich.table.Table, None, None]:
        self.columns: Iterable[str | rich.progress.ProgressColumn]
        for task in self.tasks:
            if task.fields.get("progress_type") == "summary":
                self.columns = (
                    "[magenta]{task.description}",
                    rich.progress.BarColumn(bar_width=None),
                    "[progress.percentage]{task.percentage:>3.0f}%",
                    "•",
                    "[green]{task.completed}/{task.total} completed",
                )
            if task.fields.get("progress_type") == "download":
                self.columns = (
                    "[blue]{task.description}",
                    rich.progress.BarColumn(bar_width=None),
                    "[progress.percentage]{task.percentage:>3.1f}%",
                    "•",
                    rich.progress.DownloadColumn(),
                    "•",
                    rich.progress.TransferSpeedColumn(),
                )
            if task.fields.get("progress_type") == "singularity_pull":
                self.columns = (
                    "[magenta]{task.description}",
                    "[blue]{task.fields[current_log]}",
                    rich.progress.BarColumn(bar_width=None),
                )
            yield self.make_tasks_table([task])

    # These two functions allow callers not having to track the main TaskID
    # They are pass-through functions to the rich.progress methods
    def add_main_task(self, **kwargs) -> rich.progress.TaskID:
        """Add a top-level task to the progress bar.
        This task will be used to track the overall progress of the container downloads.
        """
        self.main_task = self.add_task(
            "Container download",
            progress_type="summary",
            **kwargs,
        )
        return self.main_task

    def update_main_task(self, **kwargs) -> None:
        """Update the top-level task with new information."""
        self.update(self.main_task, **kwargs)

    @contextlib.contextmanager
    def sub_task(self, *args, **kwargs) -> Generator[rich.progress.TaskID, None, None]:
        """Context manager to create a sub-task under the main task."""
        task = self.add_task(*args, **kwargs)
        try:
            yield task
        finally:
            self.remove_task(task)


class FileDownloader:
    """Class to download files.

    Downloads are done in parallel using threads and progress is shown in the progress bar.
    """

    def __init__(self, progress: DownloadProgress) -> None:
        self.progress = progress
        self.kill_with_fire = False

    def download_files_in_parallel(
        self,
        download_files: Iterable[Tuple[str, str]],
        parallel_downloads: int,
    ) -> Generator[str, None, None]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_downloads) as pool:
            # Kick off concurrent downloads
            future_downloads = [
                pool.submit(self.download_file, remote_path, output_path)
                for (remote_path, output_path) in download_files
            ]

            # Make ctrl-c work with multi-threading
            self.kill_with_fire = False

            try:
                # Iterate over each threaded download, waiting for them to finish
                for future in concurrent.futures.as_completed(future_downloads):
                    output_path = future.result()
                    yield output_path

            except KeyboardInterrupt:
                # Cancel the future threads that haven't started yet
                for future in future_downloads:
                    future.cancel()
                # Set the variable that the threaded function looks for
                # Will trigger an exception from each active thread
                self.kill_with_fire = True
                # Re-raise exception on the main thread
                raise

    def download_file(self, remote_path: str, output_path: str) -> str:
        """Download a file from the web.

        Use native Python to download the file. Progress is shown in the progress bar
        as a new task (of type "download").

        This method is integrated with the above `download_files_in_parallel` method. The
        `self.kill_with_fire` variable is a sentinel used to check if the user has hit ctrl-c.

        Args:
            remote_path (str): Source URL of the file to download
            output_path (str): The target output path
        """
        log.debug(f"Downloading '{remote_path}' to {output_path}")

        # Set up download progress bar as a new task
        nice_name = remote_path.split("/")[-1][:50]
        with self.progress.sub_task(nice_name, start=False, total=False, progress_type="download") as task:
            # Open file handle and download
            # This temporary will be automatically renamed to the target if there are no errors
            with intermediate_file(output_path) as fh:
                # Disable caching as this breaks streamed downloads
                with requests_cache.disabled():
                    r = requests.get(remote_path, allow_redirects=True, stream=True, timeout=60 * 5)
                    filesize = r.headers.get("Content-length")
                    if filesize:
                        self.progress.update(task, total=int(filesize))
                        self.progress.start_task(task)

                    # Stream download
                    has_content = False
                    for data in r.iter_content(chunk_size=io.DEFAULT_BUFFER_SIZE):
                        # Check that the user didn't hit ctrl-c
                        if self.kill_with_fire:
                            raise KeyboardInterrupt
                        self.progress.update(task, advance=len(data))
                        fh.write(data)
                        has_content = True

                    # Check that we actually downloaded something
                    if not has_content:
                        raise DownloadError(f"Downloaded file '{remote_path}' is empty")

        return output_path
