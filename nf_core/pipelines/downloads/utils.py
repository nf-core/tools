import contextlib
import logging
import os
import tempfile
from typing import Generator, Iterable

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

    # These functions allow callers not having to track the main TaskID
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
