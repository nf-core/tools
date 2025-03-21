import logging
import os

import rich
import questionary

from nf_core.test_datasets.test_datasets_utils import (
    get_remote_branches,
    list_files_by_branch,
)
from nf_core.utils import rich_force_colors, nfcore_question_style

log = logging.getLogger(__name__)
stdout = rich.console.Console(force_terminal=rich_force_colors())

# Files / directories starting with one of the following in a git tree are ignored:
IGNORED_FILE_PREFIXES = [".", "CITATION", "LICENSE", "README", "docs", ]


def test_datasets_list_branches(ctx):
    remote_branches = get_remote_branches()
    out = os.linesep.join(remote_branches)
    stdout.print(out)


def test_datasets_list_remote(ctx, branch):

    tree = list_files_by_branch(branch, IGNORED_FILE_PREFIXES)

    out = ""
    for b in tree.keys():
        files = sorted(tree[b])
        for f in files:
            out += f"(Branch: {b}) {f}" + os.linesep

    stdout.print(out)


def test_datasets_search(ctx, branch, generate_nf_path):
    stdout.print("Searching files on branch: ", branch)
    tree = list_files_by_branch(branch, IGNORED_FILE_PREFIXES)
    files = []
    for k,v  in tree.items():
        files += v

    file = questionary.autocomplete(
        "Query:",
        choices=files,
        style=nfcore_question_style,
    ).unsafe_ask()
    
    if generate_nf_path:
        out = "params." 
        out += "modules_" if branch == "modules" else "pipelines_"
        out += f"testdata_base_path + \"{file}\""
        out = f"file({out}, checkIfExists: true)"
        stdout.print(out)
    else:
        stdout.print(file)
