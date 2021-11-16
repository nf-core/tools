import fnmatch
import io
import logging
import os

import rich
from rich.console import Console
from rich.table import Table

import nf_core.utils

log = logging.getLogger(__name__)

# Create a console used by all lint tests
console = Console(force_terminal=nf_core.utils.rich_force_colors())


def print_joint_summary(lint_obj, module_lint_obj):
    """Print a joint summary of the general pipe lint tests and the module lint tests"""
    nbr_passed = len(lint_obj.passed) + len(module_lint_obj.passed)
    nbr_ignored = len(lint_obj.ignored)
    nbr_fixed = len(lint_obj.fixed)
    nbr_warned = len(lint_obj.warned) + len(module_lint_obj.warned)
    nbr_failed = len(lint_obj.failed) + len(module_lint_obj.failed)

    def _s(some_length):
        return "" if some_length == 1 else "s"

    summary_colour = "red" if nbr_failed > 0 else "green"
    table = Table(box=rich.box.ROUNDED, style=summary_colour)
    table.add_column(f"LINT RESULTS SUMMARY".format(nbr_passed), no_wrap=True)
    table.add_row(r"[green][✔] {:>3} Test{} Passed".format(nbr_passed, _s(nbr_passed)))
    if nbr_fixed:
        table.add_row(r"[bright blue][?] {:>3} Test{} Fixed".format(nbr_fixed, _s(nbr_fixed)))
    table.add_row(r"[grey58][?] {:>3} Test{} Ignored".format(nbr_ignored, _s(nbr_ignored)))
    table.add_row(r"[yellow][!] {:>3} Test Warning{}".format(nbr_warned, _s(nbr_warned)))
    table.add_row(r"[red][✗] {:>3} Test{} Failed".format(nbr_failed, _s(nbr_failed)))
    console.print(table)


def print_fixes(lint_obj, module_lint_obj):
    """Prints available and applied fixes"""

    if len(lint_obj.could_fix):
        fix_cmd = "nf-core lint {}--fix {}".format(
            "" if lint_obj.wf_path == "." else f"--dir {lint_obj.wf_path}", " --fix ".join(lint_obj.could_fix)
        )
        console.print(
            f"\nTip: Some of these linting errors can automatically be resolved with the following command:\n\n[blue]    {fix_cmd}\n"
        )
    if len(lint_obj.fix):
        console.print(
            "Automatic fixes applied. Please check with 'git diff' and revert any changes you do not want with 'git checkout <file>'."
        )

def find_todos(self):
    passed = []
    warned = []
    failed = []
    file_paths = []

    ignore = [".git"]
    if os.path.isfile(os.path.join(self.wf_path, ".gitignore")):
        with io.open(os.path.join(self.wf_path, ".gitignore"), "rt", encoding="latin1") as fh:
            for l in fh:
                ignore.append(os.path.basename(l.strip().rstrip("/")))
    for root, dirs, files in os.walk(self.wf_path, topdown=True):
        # Ignore files
        for i_base in ignore:
            i = os.path.join(root, i_base)
            dirs[:] = [d for d in dirs if not fnmatch.fnmatch(os.path.join(root, d), i)]
            files[:] = [f for f in files if not fnmatch.fnmatch(os.path.join(root, f), i)]
        for fname in files:
            try:
                with io.open(os.path.join(root, fname), "rt", encoding="latin1") as fh:
                    for l in fh:
                        if "TODO nf-core" in l:
                            l = (
                                l.replace("<!--", "")
                                .replace("-->", "")
                                .replace("# TODO nf-core: ", "")
                                .replace("// TODO nf-core: ", "")
                                .replace("TODO nf-core: ", "")
                                .strip()
                            )
                            warned.append("TODO string in `{}`: _{}_".format(fname, l))
                            file_paths.append(os.path.join(root, fname))
            except FileNotFoundError:
                log.debug(f"Could not open file {fname} in pipeline_todos lint test")
    # HACK file paths are returned to allow usage of this function in modules/lint.py
    # Needs to be refactored!
    return {"passed": passed, "warned": warned, "failed": failed, "file_paths": file_paths}
