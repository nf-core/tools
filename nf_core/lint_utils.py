import rich
from rich.console import Console
from rich.table import Table
import logging

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
        fix_cmd = "nf-core lint {} --fix {}".format(lint_obj.wf_path, " --fix ".join(lint_obj.could_fix))
        console.print(
            f"\nTip: Some of these linting errors can automatically be resolved with the following command:\n\n[blue]    {fix_cmd}\n"
        )
    if len(lint_obj.fix):
        console.print(
            "Automatic fixes applied. Please check with 'git diff' and revert any changes you do not want with 'git checkout <file>'."
        )
