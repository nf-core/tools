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
    # TODO: fetch Branches
    # TODO: fetch Trees for branches
    # TODO: Search through trees
    # TODO: Sort output by branch
    pass