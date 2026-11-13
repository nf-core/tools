from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from nf_core.utils import get_wf_files

if TYPE_CHECKING:
    from nf_core.pipelines.lint import PipelineLint

log = logging.getLogger(__name__)


def pipeline_if_empty_null(
    self: PipelineLint | None, root_dir: Path | None = None
) -> dict[str, list[str] | list[Path]]:
    """Check for ifEmpty(null)

    There are two general cases for workflows to use the channel operator `ifEmpty`:
        1. `ifEmpty( [ ] )` to ensure a process executes, for example when an input file is optional (although this can be replaced by `toList()`).
        2. When a channel should not be empty and throws an error `ifEmpty { error ... }`, e.g. reading from an empty samplesheet.

    There are multiple examples of workflows that inject null objects into channels using `ifEmpty(null)`, which can cause unhandled null pointer exceptions.
    This lint test throws warnings for those instances.
    """

    passed: list[str] = []
    warned: list[str] = []
    file_paths: list[Path] = []
    pattern = re.compile(r"ifEmpty\s*\(\s*null\s*\)")

    # Pipelines don't provide a path, so use the workflow path.
    # Modules run this function twice and provide a string path
    if root_dir is None:
        if self is None:
            raise ValueError("Either a PipelineLint object or root_dir must be provided")
        root_dir = self.wf_path

    for file in get_wf_files(root_dir):
        try:
            with open(file, encoding="latin1") as fh:
                for line in fh:
                    if re.findall(pattern, line):
                        warned.append(f"`ifEmpty(null)` found in `{file}`: _{line}_")
                        file_paths.append(file)
        except FileNotFoundError:
            log.debug(f"Could not open file {file} in pipeline_if_empty_null lint test")

    if len(warned) == 0:
        passed.append("No `ifEmpty(null)` strings found")

    # return file_paths for use in subworkflow lint
    return {"passed": passed, "warned": warned, "file_paths": file_paths}
