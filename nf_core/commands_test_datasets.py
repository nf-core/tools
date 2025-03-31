import logging
import os

import questionary
import rich

from nf_core.test_datasets.list import list_datasets
from nf_core.test_datasets.test_datasets_utils import (
    MODULES_BRANCH_NAME,
    create_download_url,
    create_pretty_nf_path,
    get_or_prompt_branch,
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
    """
    List all branches on the nf-core/test-datasets repository.
    Only lists test data and module test data based on the curated list
    of pipeline names [on the website](https://raw.githubusercontent.com/nf-core/website/refs/heads/main/public/pipeline_names.json).
    """
    remote_branches = get_remote_branch_names()
    out = os.linesep.join(remote_branches)
    stdout.print(out)


def test_datasets_list_remote(ctx, maybe_branch, generate_nf_path, generate_dl_url):
    """
    List all files on a given branch in the remote nf-core/testdatasets repository on github.
    The resulting files can be parsed as a nextflow path or a url for downloading.
    """
    list_datasets(maybe_branch, generate_nf_path, generate_dl_url, ignored_file_prefixes=IGNORED_FILE_PREFIXES)


def test_datasets_search(ctx, maybe_branch, generate_nf_path, generate_dl_url):
    """
    Search all files on a given branch in the remote nf-core/testdatasets repository on github
    with an interactive autocompleting prompt and print the file matching the query.
    Specifying a branch is required.
    The resulting file can optionally be parsed as a nextflow path or a url for downloading
    """
    branch, all_branches = get_or_prompt_branch(maybe_branch)

    stdout.print("Searching files on branch: ", branch)
    tree = list_files_by_branch(branch, all_branches, IGNORED_FILE_PREFIXES)
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
    elif generate_dl_url:
        stdout.print(create_download_url(branch, selection))
    else:
        stdout.print(selection)
