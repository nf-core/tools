from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from nf_core.utils import get_wf_files

if TYPE_CHECKING:
    from nf_core.pipelines.lint import PipelineLint

log = logging.getLogger(__name__)


def pipeline_todos(self: PipelineLint | None, root_dir: Path | None = None) -> dict[str, list[str] | list[Path]]:
    """Check for nf-core *TODO* lines.

    The nf-core workflow template contains a number of comment lines to help developers
    of new pipelines know where they need to edit files and add content.
    They typically have the following format:

    .. code-block:: groovy

        // TODO nf-core: Make some kind of change to the workflow here

    ..or in markdown:

    .. code-block:: html

        <!-- TODO nf-core: Add some detail to the docs here -->

    This lint test runs through all files in the pipeline and searches for these lines.
    If any are found they will throw a warning.

    .. tip:: Note that many GUI code editors have plugins to list all instances of *TODO*
              in a given project directory. This is a very quick and convenient way to get
              started on your pipeline!
    """
    passed: list[str] = []
    warned: list[str] = []
    file_paths: list[Path] = []

    # Pipelines don't provide a path, so use the workflow path.
    # Modules run this function twice and provide a string path
    if root_dir is None:
        if self is None:
            raise ValueError("Either a PipelineLint object or root_dir must be provided")
        root_dir = self.wf_path

    for path in get_wf_files(root_dir):
        # Ignore ro-crate-metadata.json to avoid warnings when TODOs are not deleted.
        if path.name == "ro-crate-metadata.json":
            continue
        fname = path.name
        try:
            with open(path, encoding="latin1") as fh:
                for line in fh:
                    if "TODO nf-core" in line:
                        line = (
                            line.replace("<!--", "")
                            .replace("-->", "")
                            .replace("# TODO nf-core: ", "")
                            .replace("// TODO nf-core: ", "")
                            .replace("TODO nf-core: ", "")
                            .strip()
                        )
                        warned.append(f"TODO string in `{fname}`: _{line}_")
                        file_paths.append(path)
        except FileNotFoundError:
            log.debug(f"Could not open file {fname} in pipeline_todos lint test")

    if len(warned) == 0:
        passed.append("No TODO strings found")

    # HACK file paths are returned to allow usage of this function in modules/lint.py
    # Needs to be refactored!
    return {"passed": passed, "warned": warned, "file_paths": file_paths}
