import logging
import os
import sys
import time

import rich

from nf_core.test_datasets.test_datasets_utils import list_files_by_branch, list_files_by_branch_async
from nf_core.utils import rich_force_colors

log = logging.getLogger(__name__)
stdout = rich.console.Console(force_terminal=rich_force_colors())


def test_datasets_list_remote(ctx, branch):

    #tree = list_files_by_branch(branch)
    tree = list_files_by_branch_async(branch)

    out = ""
    for b in tree.keys():
        files = sorted(tree[b])
        for f in files:
            out += f"(Branch: {b}) {f}" + os.linesep

    stdout.print(out)


def test_datasets_search(ctx, query, branch):
    log.debug(f"test-datasets search query: {query}")
    #tree = list_files_by_branch(branch)
    # concurrent requests for speed-up
    tree = list_files_by_branch_async(branch)
    log.debug(f"Searching the tree of {len(tree.keys())} remote branches ...")

    out = ""
    for b in tree.keys():
        files = sorted(tree[b])
        for f in files:
            if query in f:
                out += f"(Branch: {b}) {f}" + os.linesep

    stdout.print(out)
