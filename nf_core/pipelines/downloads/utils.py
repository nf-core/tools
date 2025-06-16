import concurrent.futures
import contextlib
import enum
import io
import logging
import os
import tempfile
from typing import Callable, Dict, Generator, Iterable, List, Optional, Tuple

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
            if task.fields.get("progress_type") == "docker_pull":
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

    Downloads are done in parallel using threads. Progress of each download
    is shown in a progress bar.

    Users can hook a callback method to be notified after each download.
    """

    # Enum to report the status of a download thread
    Status = enum.Enum("Status", "CANCELLED PENDING RUNNING DONE ERROR")

    def __init__(self, progress: DownloadProgress) -> None:
        """Initialise the FileDownloader object.

        Args:
            progress (DownloadProgress): The progress bar object to use for tracking downloads.
        """
        self.progress = progress
        self.kill_with_fire = False

    def parse_future_status(self, future: concurrent.futures.Future) -> Status:
        """Parse the status of a future object."""
        if future.running():
            return self.Status.RUNNING
        if future.cancelled():
            return self.Status.CANCELLED
        if future.done():
            if future.exception():
                return self.Status.ERROR
            return self.Status.DONE
        return self.Status.PENDING

    def download_files_in_parallel(
        self,
        download_files: Iterable[Tuple[str, str]],
        parallel_downloads: int,
        callback: Optional[Callable[[Tuple[str, str], Status], None]] = None,
    ) -> List[Tuple[str, str]]:
        """Download multiple files in parallel.

        Args:
            download_files (Iterable[Tuple[str, str]]): List of tuples with the remote URL and the local output path.
            parallel_downloads (int): Number of parallel downloads to run.
            callback (Callable[[Tuple[str, str], Status], None]): Optional allback function to call after each download.
                         The function must take two arguments: the download tuple and the status of the download thread.
        """

        # Make ctrl-c work with multi-threading
        self.kill_with_fire = False

        # Track the download threads
        future_downloads: Dict[concurrent.futures.Future, Tuple[str, str]] = {}

        # List to store *successful* downloads
        successful_downloads = []

        def successful_download_callback(future: concurrent.futures.Future) -> None:
            if future.done() and not future.cancelled() and future.exception() is None:
                successful_downloads.append(future_downloads[future])

        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_downloads) as pool:
            # The entire block needs to be monitored for KeyboardInterrupt so that ntermediate files
            # can be cleaned up properly.
            try:
                for input_params in download_files:
                    (remote_path, output_path) = input_params
                    # Create the download thread as a Future object
                    future = pool.submit(self.download_file, remote_path, output_path)
                    future_downloads[future] = input_params
                    # Callback to record successful downloads
                    future.add_done_callback(successful_download_callback)
                    # User callback function (if provided)
                    if callback:
                        future.add_done_callback(lambda f: callback(future_downloads[f], self.parse_future_status(f)))

                completed_futures = concurrent.futures.wait(
                    future_downloads, return_when=concurrent.futures.ALL_COMPLETED
                )
                # Get all the exceptions and exclude BaseException-based ones (e.g. KeyboardInterrupt)
                exceptions = [
                    exc for exc in (f.exception() for f in completed_futures.done) if isinstance(exc, Exception)
                ]
                if exceptions:
                    raise DownloadError("Download errors", exceptions)

            except KeyboardInterrupt:
                # Cancel the future threads that haven't started yet
                for future in future_downloads:
                    future.cancel()
                # Set the variable that the threaded function looks for
                # Will trigger an exception from each active thread
                self.kill_with_fire = True
                # Re-raise exception on the main thread
                raise

        return successful_downloads

    def download_file(self, remote_path: str, output_path: str) -> None:
        """Download a file from the web.

        Use native Python to download the file. Progress is shown in the progress bar
        as a new task (of type "download").

        This method is integrated with the above `download_files_in_parallel` method. The
        `self.kill_with_fire` variable is a sentinel used to check if the user has hit ctrl-c.

        Args:
            remote_path (str): Source URL of the file to download
            output_path (str): The target output path
        """
        log.debug(f"Downloading '{remote_path}' to '{output_path}'")

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
