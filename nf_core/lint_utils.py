import logging

import rich
from rich.console import Console
from rich.table import Table

import nf_core.utils
from nf_core.utils import plural_s as _s

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

    summary_colour = "red" if nbr_failed > 0 else "green"
    table = Table(box=rich.box.ROUNDED, style=summary_colour)
    table.add_column("LINT RESULTS SUMMARY", no_wrap=True)
    table.add_row(rf"[green][✔] {nbr_passed:>3} Test{_s(nbr_passed)} Passed")
    if nbr_fixed:
        table.add_row(rf"[bright blue][?] {nbr_fixed:>3} Test{_s(nbr_fixed)} Fixed")
    table.add_row(rf"[grey58][?] {nbr_ignored:>3} Test{_s(nbr_ignored)} Ignored")
    table.add_row(rf"[yellow][!] {nbr_warned:>3} Test Warning{_s(nbr_warned)}")
    table.add_row(rf"[red][✗] {nbr_failed:>3} Test{_s(nbr_failed)} Failed")
    console.print(table)


def print_fixes(lint_obj, module_lint_obj):
    """Prints available and applied fixes"""

    if len(lint_obj.could_fix):
        fix_cmd = "nf-core lint {} --fix {}".format(
            "" if lint_obj.wf_path == "." else f"--dir {lint_obj.wf_path}", " --fix ".join(lint_obj.could_fix)
        )
        console.print(
            f"\nTip: Some of these linting errors can automatically be resolved with the following command:\n\n[blue]    {fix_cmd}\n"
        )
    if len(lint_obj.fix):
        console.print(
            "Automatic fixes applied. Please check with 'git diff' and revert any changes you do not want with 'git checkout <file>'."
        )
