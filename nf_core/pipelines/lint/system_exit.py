import logging
import re
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

from nf_core import astgrep

if TYPE_CHECKING:
    from ast_grep_py import SgNode

log = logging.getLogger(__name__)

FALLBACK_REGEX = re.compile(r"System\.exit\s*\((?!\s*0\s*\))")


def find_system_exit(root: "SgNode") -> Iterator["SgNode"]:
    """Yield every ``System.exit(...)`` call below ``root``, except ``System.exit(0)``."""
    for call in root.find_all(pattern="System.exit($CODE)"):
        code = call.get_match("CODE")
        if code is None or code.text() != "0":
            yield call


def system_exit(self):
    """Check for System.exit calls in groovy/nextflow code

    Calls to System.exit(1) should be replaced by throwing errors

    This lint test looks for all calls to `System.exit`
    in any file with the `.nf` or `.groovy` extension

    Nextflow/Groovy files are matched structurally with :func:`find_system_exit`.
    See ``nf_core.astgrep.find_nodes`` for the structural vs regex-fallback behaviour.
    """
    root_dir = Path(self.wf_path)
    files = list(root_dir.rglob("*.nf")) + list(root_dir.rglob("*.groovy"))

    warned = [
        f"`System.exit` call found in {file.name}: _{text}_  [line {line_num}]"
        for file, line_num, text in astgrep.find_nodes(
            find_system_exit, files, fallback=FALLBACK_REGEX, name="system_exit"
        )
    ]
    passed = [] if warned else ["No `System.exit` calls found"]

    return {"passed": passed, "warned": warned}
