import logging
import re
from collections.abc import Iterator
from typing import TYPE_CHECKING

from nf_core import astgrep
from nf_core.utils import get_wf_files

if TYPE_CHECKING:
    from ast_grep_py import SgNode

log = logging.getLogger(__name__)

FALLBACK_REGEX = re.compile(r"ifEmpty\s*\(\s*null\s*\)")


def find_if_empty_null(root: "SgNode") -> Iterator["SgNode"]:
    """Yield every ``ifEmpty(null)`` call below ``root``.

    Covers ``ch.ifEmpty(null)``, chained receivers such as
    ``Channel.fromPath(x).ifEmpty(null)`` and the piped ``ch | ifEmpty(null)``.
    ``ifEmpty`` / ``null`` appearing elsewhere (comments, strings, other
    arguments) are not flagged.
    """
    for call in root.find_all(any=[{"kind": "method_call"}, {"kind": "function_call"}]):
        children = call.children()
        # the method name is the node right before the argument list's "("
        paren = next((i for i, child in enumerate(children) if child.kind() == "("), 0)
        if paren == 0 or children[paren - 1].text() != "ifEmpty":
            continue
        args = [child.text() for child in children[paren + 1 :] if child.kind() == "simple_expression"]
        if args == ["null"]:
            yield call


def pipeline_if_empty_null(self, root_dir=None):
    """Check for ifEmpty(null)

    There must be no `ifEmpty(null)` statements in a pipeline, as they cause unexpected behaviour.
    To skip processing in the absence of input data, use `ifEmpty([])` (to keep processes executing on optional inputs),
    or `ifEmpty { error ... }` (to raise errors where processing should not proceed).

    There are multiple examples of workflows that inject null objects into channels using `ifEmpty(null)`, which can cause unhandled null pointer exceptions.
    This lint test throws warnings for those instances.

    Nextflow files are matched structurally with :func:`find_if_empty_null`.
    See ``nf_core.astgrep.find_nodes`` for the structural vs regex-fallback behaviour.
    """
    # Pipelines don't provide a path, so use the workflow path.
    # Modules run this function twice and provide a string path
    if root_dir is None:
        root_dir = self.wf_path

    warned = []
    file_paths = []
    matches = astgrep.find_nodes(
        find_if_empty_null, get_wf_files(root_dir), fallback=FALLBACK_REGEX, name="pipeline_if_empty_null"
    )
    for file, line_num, text in matches:
        warned.append(f"`ifEmpty(null)` found in `{file}` [line {line_num}]: _{text}_")
        file_paths.append(file)

    passed = [] if warned else ["No `ifEmpty(null)` strings found"]

    # return file_paths for use in subworkflow lint
    return {"passed": passed, "warned": warned, "file_paths": file_paths}
