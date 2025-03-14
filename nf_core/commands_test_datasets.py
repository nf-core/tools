import logging
import sys

import rich

from nf_core.test_datasets.test_datasets_utils import get_remote_branches, get_remote_tree_for_branch
from nf_core.utils import rich_force_colors

log = logging.getLogger(__name__)
stdout = rich.console.Console(force_terminal=rich_force_colors())

def test_datasets_list_remote(ctx, branch):

    # debug output
    branches = sorted(get_remote_branches())
    trees = dict()
    for b in branches:
        stdout.print(b)
        trees[b] = get_remote_tree_for_branch(b)

    # debug output
    stdout.print(trees)
