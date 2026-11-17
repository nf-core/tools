import fnmatch
import logging
import os
import re
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

from nf_core import astgrep

if TYPE_CHECKING:
    from ast_grep_py import SgNode

log = logging.getLogger(__name__)

FALLBACK_REGEX = re.compile(r"TODO nf-core")


def find_todo_comments(root: "SgNode") -> Iterator["SgNode"]:
    """Yield every comment node containing ``TODO nf-core`` (strings and code are not flagged)."""
    return iter(root.find_all(any=[{"kind": "line_comment"}, {"kind": "block_comment"}], regex="TODO nf-core"))


def _clean_todo(text: str) -> str:
    """Reduce a matched comment to the TODO text itself."""
    for line in text.splitlines():
        if "TODO nf-core" in line:
            text = line
            break
    return (
        text.replace("<!--", "")
        .replace("-->", "")
        .replace("/*", "")
        .replace("*/", "")
        .replace("*", "")
        .replace("# TODO nf-core: ", "")
        .replace("// TODO nf-core: ", "")
        .replace("TODO nf-core: ", "")
        .strip()
    )


def pipeline_todos(self, root_dir=None):
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

    Nextflow/Groovy files are matched structurally via
    :func:`find_todo_comments` when the parser is available (a "TODO nf-core"
    inside a string is not flagged); all other files are searched line by line.

    .. tip:: Note that many GUI code editors have plugins to list all instances of *TODO*
              in a given project directory. This is a very quick and convenient way to get
              started on your pipeline!
    """
    passed = []
    warned = []
    file_paths = []

    # Pipelines don't provide a path, so use the workflow path.
    # Modules run this function twice and provide a string path
    if root_dir is None:
        root_dir = self.wf_path

    # Ignore ro-crate-metadata.json to avoid warnings when TODOs are not deleted.
    ignore = [".git", "ro-crate-metadata.json"]
    if Path(root_dir, ".gitignore").is_file():
        with open(Path(root_dir, ".gitignore"), encoding="latin1") as fh:
            for line in fh:
                ignore.append(Path(line.strip().rstrip("/")).name)

    to_check = []
    for root, dirs, files in os.walk(root_dir, topdown=True):
        # Ignore files
        for i_base in ignore:
            i = str(Path(root, i_base))
            dirs[:] = [d for d in dirs if not fnmatch.fnmatch(str(Path(root, d)), i)]
            files[:] = [f for f in files if not fnmatch.fnmatch(str(Path(root, f)), i)]
        to_check.extend(Path(root, fname) for fname in files)

    matches = astgrep.find_nodes(
        find_todo_comments, to_check, fallback=FALLBACK_REGEX, regex_unparseable=True, name="pipeline_todos"
    )
    for file, _line_num, text in matches:
        warned.append(f"TODO string in `{file.name}`: _{_clean_todo(text)}_")
        file_paths.append(file)

    if len(warned) == 0:
        passed.append("No TODO strings found")

    return {"passed": passed, "warned": warned, "file_paths": file_paths}
