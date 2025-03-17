import logging
import sys

import rich

from nf_core.test_datasets.test_datasets_utils import list_files_by_branch
from nf_core.utils import rich_force_colors

log = logging.getLogger(__name__)
stdout = rich.console.Console(force_terminal=rich_force_colors())

def test_datasets_list_remote(ctx, branch):

    tree = list_files_by_branch(branch)

    for b in tree.keys():
        files = sorted(tree[b])
        for f in files:
            stdout.print(f"(Branch: {b}) {f}")


def test_datasets_search(ctx, query, branch):
    log.debug(f"test-datasets search query: {query}")
    tree = list_files_by_branch(branch)
    log.debug(f"Searching the tree of {len(tree.keys())} remote branches ...")

    for b in tree.keys():
        files = sorted(tree[b])
        for f in files:
            if query in f:
                stdout.print(f"(Branch: {b}) {f}")
