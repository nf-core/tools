import json
import logging
import subprocess
from pathlib import Path

import rich
import yaml
from rich.console import Console
from rich.table import Table

import nf_core.utils
from nf_core import __version__
from nf_core.utils import plural_s as _s
from nf_core.utils import strip_ansi_codes

log = logging.getLogger(__name__)

# Create a console used by all lint tests
console = Console(force_terminal=nf_core.utils.rich_force_colors())


def print_results_plain_text(results_list, directory=None, component_type=None):
    """Print lint results in plain text format.

    Args:
        results_list: List of tuples (results, symbol, label, color, show_condition)
        directory: Base directory for relative paths (for component linting)
        component_type: "modules" or "subworkflows" (for component linting)
    """
    tools_version = "dev" if "dev" in __version__ else __version__

    def print_lines(text, strip_ansi=False):
        """Print text line by line, skipping empty lines."""
        text = strip_ansi_codes(str(text)) if strip_ansi else str(text)
        for line in text.strip().split("\n"):
            if line := line.strip():
                console.print(line)

    for results, symbol, label, color, show in results_list:
        if show and results:
            label_suffix = component_type[:-1].title() if component_type else "Pipeline"
            console.print(
                f"\n[{color}][bold][{symbol}] {len(results)} {label_suffix} Test{_s(results)} {label}[/bold][/{color}]"
            )
            for r in results:
                if isinstance(r, tuple):
                    # Pipeline results: (eid, msg)
                    eid, msg = r
                    console.print(
                        f"\n[{color}]{eid}[/{color}] https://nf-co.re/tools/docs/{tools_version}/pipeline_lint_tests/{eid}"
                    )
                    print_lines(msg, strip_ansi=True)
                else:
                    # Component results: LintResult objects
                    console.print(f"\n[{color}]{r.component_name}[/{color}] {r.lint_test}")
                    console.print(Path(r.file_path).relative_to(directory))
                    console.print(
                        f"https://nf-co.re/docs/nf-core-tools/api_reference/{tools_version}/{component_type[:-1]}_lint_tests/{r.parent_lint_test}"
                    )
                    print_lines(r.message)


def print_summary(rows, plain_text=False, summary_colour=None):
    """Print a summary table in plain text or rich format.

    Args:
        rows: List of tuples (count, icon, label, color, always_show)
        plain_text: If True, print in plain text format
        summary_colour: Color for the rich table border (default: auto based on failures)
    """
    if plain_text:
        console.print("\n[bold]LINT RESULTS SUMMARY[/bold]")
        for count, icon, label, color, always_show in rows:
            if always_show or count:
                console.print(f"[{color}][{icon}] {count:>3} {label}[/{color}]")
    else:
        table = Table(box=rich.box.ROUNDED, style=summary_colour)
        table.add_column("LINT RESULTS SUMMARY", no_wrap=True)
        for count, icon, label, color, always_show in rows:
            if always_show or count:
                table.add_row(rf"[{color}][{icon}] {count:>3} {label}")
        console.print(table)


def print_joint_summary(lint_obj, module_lint_obj, subworkflow_lint_obj, plain_text=False):
    """Print a joint summary of the general pipe lint tests and the module and subworkflow lint tests"""
    swf_passed = 0
    swf_warned = 0
    swf_failed = 0
    module_passed = 0
    module_warned = 0
    module_failed = 0
    if subworkflow_lint_obj is not None:
        swf_passed = len(subworkflow_lint_obj.passed)
        swf_warned = len(subworkflow_lint_obj.warned)
        swf_failed = len(subworkflow_lint_obj.failed)
    if module_lint_obj is not None:
        module_passed = len(module_lint_obj.passed)
        module_warned = len(module_lint_obj.warned)
        module_failed = len(module_lint_obj.failed)
    nbr_passed = len(lint_obj.passed) + module_passed + swf_passed
    nbr_ignored = len(lint_obj.ignored)
    nbr_fixed = len(lint_obj.fixed)
    nbr_warned = len(lint_obj.warned) + module_warned + swf_warned
    nbr_failed = len(lint_obj.failed) + module_failed + swf_failed

    rows = [
        (nbr_passed, "✔", f"Test{_s(nbr_passed)} Passed", "green", True),
        (nbr_fixed, "?", f"Test{_s(nbr_fixed)} Fixed", "bright_blue", False),
        (nbr_ignored, "?", f"Test{_s(nbr_ignored)} Ignored", "grey58", True),
        (nbr_warned, "!", f"Test Warning{_s(nbr_warned)}", "yellow", True),
        (nbr_failed, "✗", f"Test{_s(nbr_failed)} Failed", "red", True),
    ]
    summary_colour = "red" if nbr_failed > 0 else "green"
    print_summary(rows, plain_text, summary_colour)


def print_fixes(lint_obj, plain_text=False):
    """Prints available and applied fixes"""
    if lint_obj.could_fix:
        fix_flags = "".join([f" --fix {fix}" for fix in lint_obj.could_fix])
        wf_dir = "" if lint_obj.wf_path == "." else f"--dir {lint_obj.wf_path}"
        fix_cmd = f"nf-core pipelines lint {wf_dir} {fix_flags}"
        msg = f"\nTip: Some of these linting errors can automatically be resolved with the following command:\n\n    {fix_cmd}\n"
        console.print(msg if plain_text else f"[blue]{msg}")
    if len(lint_obj.fix):
        console.print(
            "Automatic fixes applied. Please check with 'git diff' and revert any changes you do not want with 'git checkout <file>'."
        )


def check_git_repo() -> bool:
    """Check if the current directory is a git repository."""
    try:
        subprocess.check_output(["git", "rev-parse", "--is-inside-work-tree"])
        return True
    except subprocess.CalledProcessError:
        return False


def run_prettier_on_file(file: Path | str | list[str]) -> None:
    """Run the pre-commit hook prettier on a file.

    Args:
        file (Path | str): A file identifier as a string or pathlib.Path.

    Warns:
        If Prettier is not installed, a warning is logged.
    """

    is_git = check_git_repo()

    nf_core_pre_commit_config = Path(nf_core.__file__).parent / ".pre-commit-prettier-config.yaml"
    args = ["pre-commit", "run", "--config", str(nf_core_pre_commit_config), "prettier"]
    if isinstance(file, list):
        args.extend(["--files", *file])
    else:
        args.extend(["--files", str(file)])

    if is_git:
        try:
            proc = subprocess.run(args, capture_output=True, check=True)
            log.debug(f"{proc.stdout.decode()}")
        except subprocess.CalledProcessError as e:
            if ": SyntaxError: " in e.stdout.decode():
                log.critical(f"Can't format {file} because it has a syntax error.\n{e.stdout.decode()}")
            elif "files were modified by this hook" in e.stdout.decode():
                all_lines = [line for line in e.stdout.decode().split("\n")]
                files = "\n".join(all_lines[3:])
                log.debug(f"The following files were modified by prettier:\n {files}")
            else:
                log.warning(
                    "There was an error running the prettier pre-commit hook.\n"
                    f"STDOUT: {e.stdout.decode()}\nSTDERR: {e.stderr.decode()}"
                )
    else:
        log.debug("Not in a git repository, skipping pre-commit hook.")


def dump_json_with_prettier(file_name, file_content):
    """Dump a JSON file and run prettier on it.
    Args:
        file_name (Path | str): A file identifier as a string or pathlib.Path.
        file_content (dict): Content to dump into the JSON file
    """
    with open(file_name, "w") as fh:
        json.dump(file_content, fh, indent=4)
    run_prettier_on_file(file_name)


def dump_yaml_with_prettier(file_name: Path | str, file_content: dict) -> None:
    """Dump a YAML file and run prettier on it.

    Args:
        file_name (Path | str): A file identifier as a string or pathlib.Path.
        file_content (dict): Content to dump into the YAML file
    """
    with open(file_name, "w") as fh:
        yaml.safe_dump(file_content, fh)
    run_prettier_on_file(file_name)


def ignore_file(lint_name: str, file_path: Path, dir_path: Path) -> list[list[str]]:
    """Ignore a file and add the result to the ignored list. Return the passed, failed, ignored and ignore_configs lists."""

    passed: list[str] = []
    failed: list[str] = []
    ignored: list[str] = []
    _, pipeline_conf = nf_core.utils.load_tools_config(dir_path)
    lint_conf = getattr(pipeline_conf, "lint", None) or None

    if lint_conf is None:
        ignore_entry: list[str] = []
    else:
        ignore_entry = lint_conf.get(lint_name, [])
    full_path = dir_path / file_path
    # Return a failed status if we can't find the file
    if not full_path.is_file():
        if isinstance(ignore_entry, bool) and not ignore_entry:
            ignored.append(f"`{file_path}` not found, but it is ignored.")
            ignore_entry = []
        else:
            failed.append(f"`{file_path}` not found.")
    else:
        passed.append(f"`{file_path}` found and not ignored.")

    # we handled the only case where ignore_entry should be a bool, convert it to a list, to make downstream code easier
    if isinstance(ignore_entry, bool):
        ignore_entry = []

    return [passed, failed, ignored, ignore_entry]
