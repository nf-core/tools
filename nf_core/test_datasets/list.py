import os

import rich

from nf_core.test_datasets.test_datasets_utils import (
    MODULES_BRANCH_NAME,
    create_download_url,
    create_pretty_nf_path,
    get_or_prompt_branch,
    list_files_by_branch,
)
from nf_core.utils import rich_force_colors

stdout = rich.console.Console(force_terminal=rich_force_colors())


def list_datasets(maybe_branch, generate_nf_path, generate_dl_url, ignored_file_prefixes):
    """
    List all datasets for the given branch on the nf-core/test-datasets repository.
    If the given branch is empty or None, the user is prompted to enter one.

    Only lists test data and module test data based on the curated list
    of pipeline names [on the website](https://raw.githubusercontent.com/nf-core/website/refs/heads/main/public/pipeline_names.json).

    Ignores files with prefixes given in ignored_file_prefixes.
    """
    branch, all_branches = get_or_prompt_branch(maybe_branch)

    tree = list_files_by_branch(branch, all_branches, ignored_file_prefixes)
    num_branches = len(tree.keys())

    out = ""
    for b in tree.keys():
        branch_info = f"(Branch: {b})" if num_branches > 1 else ""
        files = sorted(tree[b])
        for f in files:
            if generate_nf_path:
                out += branch_info + create_pretty_nf_path(f, branch == MODULES_BRANCH_NAME) + os.linesep
            elif generate_dl_url:
                out += branch_info + create_download_url(branch, f) + os.linesep
            else:
                out += branch_info + f + os.linesep

    stdout.print(out)
