import logging
from pathlib import Path

from nf_core import astgrep
from nf_core.utils import get_wf_files

log = logging.getLogger(__name__)

RULE_FILE = Path(__file__).parent / "rules" / "pipeline_if_empty_null.yml"


def pipeline_if_empty_null(self, root_dir=None):
    """Check for ifEmpty(null)

    There are two general cases for workflows to use the channel operator `ifEmpty`:
        1. `ifEmpty( [ ] )` to ensure a process executes, for example when an input file is optional (although this can be replaced by `toList()`).
        2. When a channel should not be empty and throws an error `ifEmpty { error ... }`, e.g. reading from an empty samplesheet.

    There are multiple examples of workflows that inject null objects into channels using `ifEmpty(null)`, which can cause unhandled null pointer exceptions.
    This lint test throws warnings for those instances.

    The match logic lives in the ast-grep rule file ``rules/pipeline_if_empty_null.yml``.
    See ``nf_core.astgrep.find_matches`` for the structural vs regex-fallback behaviour.
    """
    # Pipelines don't provide a path, so use the workflow path.
    # Modules run this function twice and provide a string path
    if root_dir is None:
        root_dir = self.wf_path

    rule = astgrep.load_rule(RULE_FILE)
    warned = []
    file_paths = []
    for file, line_num, text in astgrep.find_matches(rule, get_wf_files(root_dir)):
        warned.append(f"{rule['message']} in `{file}` [line {line_num}]: _{text}_")
        file_paths.append(file)

    passed = [] if warned else ["No `ifEmpty(null)` strings found"]

    # return file_paths for use in subworkflow lint
    return {"passed": passed, "warned": warned, "file_paths": file_paths}
