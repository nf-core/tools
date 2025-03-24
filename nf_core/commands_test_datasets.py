import logging
import os

import questionary
import rich

from nf_core.test_datasets.test_datasets_utils import (
    MODULES_BRANCH_NAME,
    create_pretty_nf_path,
    get_remote_branch_names,
    list_files_by_branch,
)
from nf_core.utils import nfcore_question_style, rich_force_colors

log = logging.getLogger(__name__)
stdout = rich.console.Console(force_terminal=rich_force_colors())

# Files / directories starting with one of the following in a git tree are ignored:
IGNORED_FILE_PREFIXES = [
    ".",
    "CITATION",
    "LICENSE",
    "README",
    "docs",
]


def test_datasets_list_branches(ctx):
    remote_branches = get_remote_branch_names()
    out = os.linesep.join(remote_branches)
    stdout.print(out)


def test_datasets_list_remote(ctx, branch, generate_nf_path):
    tree = list_files_by_branch(branch, IGNORED_FILE_PREFIXES)
    num_branches = len(tree.keys())

    out = ""
    for b in tree.keys():
        branch_info = f"(Branch: {b})" if num_branches > 1 else ""
        files = sorted(tree[b])
        for f in files:
            if generate_nf_path:
                out += branch_info + create_pretty_nf_path(f, branch == MODULES_BRANCH_NAME) + os.linesep
            else:
                out += branch_info + f + os.linesep

    stdout.print(out)


def test_datasets_search(ctx, branch, generate_nf_path):
    stdout.print("Searching files on branch: ", branch)
    tree = list_files_by_branch(branch, IGNORED_FILE_PREFIXES)
    files = sum(tree.values(), [])  # flat representation of tree

    file_selected = False
    while not file_selected:
        selection = questionary.autocomplete(
            "File:",
            choices=files,
            style=nfcore_question_style,
        ).unsafe_ask()

        file_selected = any([selection == file for file in files])
        if not file_selected:
            stdout.print("Please select a file.")

    if generate_nf_path:
        stdout.print(create_pretty_nf_path(selection, branch == MODULES_BRANCH_NAME))
    else:
        stdout.print(selection)
