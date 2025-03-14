import logging
import sys

import rich
from test_datasets.test_datasets_utils import get_remote_branches, get_remote_tree_for_branch

from nf_core.utils import rich_force_colors

log = logging.getLogger(__name__)
stdout = rich.console.Console(force_terminal=rich_force_colors())

def test_datasets_list_remote(ctx, branch):
    # TODO: List remote repositories
    pass
