import logging
import os
import sys
import time

import rich

from nf_core.test_datasets.test_datasets_utils import (
    get_remote_branches,
    list_files_by_branch,
    list_files_by_branch_async,
)
from nf_core.utils import rich_force_colors

log = logging.getLogger(__name__)
stdout = rich.console.Console(force_terminal=rich_force_colors())

# Files / directories starting with one of the following in a git tree are ignored:
IGNORED_FILE_PREFIXES = [".", "CITATION", "LICENSE", "README", "docs", ]


def test_datasets_list_branches(ctx):
    remote_branches = get_remote_branches()
    out = os.linesep.join(remote_branches)
    stdout.print(out)


def test_datasets_list_remote(ctx, asynchronous, branch):

    if ctx.obj["verbose"] and not asynchronous and not branch:
        log.warning("Using nf-core test-datasets with verbose (-v) flag and without asynchronous mode (--asynchronous) can drasticly reduce performance.")

    if asynchronous:
        tree = list_files_by_branch_async(branch, IGNORED_FILE_PREFIXES)
    else:
        tree = list_files_by_branch(branch, IGNORED_FILE_PREFIXES)

    out = ""
    for b in tree.keys():
        files = sorted(tree[b])
        for f in files:
            out += f"(Branch: {b}) {f}" + os.linesep

    stdout.print(out)


def test_datasets_search(ctx, query, asynchronous, branch, ignore_case):
    log.debug(f"test-datasets search query: {query}")

    if asynchronous:
        tree = list_files_by_branch_async(branch, IGNORED_FILE_PREFIXES)
    else:
        tree = list_files_by_branch(branch, IGNORED_FILE_PREFIXES)
    log.debug(f"Searching the tree of {len(tree.keys())} remote branches ...")

    out = ""
    for b in tree.keys():
        files = sorted(tree[b])
        for f in files:
            if (ignore_case and query.lower() in f.lower()) or query in f:
                out += f"(Branch: {b}) {f}" + os.linesep

    stdout.print(out)
