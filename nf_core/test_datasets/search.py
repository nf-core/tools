from typing import List

import questionary
import rich

from nf_core.test_datasets.test_datasets_utils import (
    IGNORED_FILE_PREFIXES,
    MODULES_BRANCH_NAME,
    create_download_url,
    create_pretty_nf_path,
    get_or_prompt_branch,
    list_files_by_branch,
)
from nf_core.utils import nfcore_question_style, rich_force_colors

stdout = rich.console.Console(force_terminal=rich_force_colors())


def search_datasets(
    maybe_branch: str = "",
    generate_nf_path: bool = False,
    generate_dl_url: bool = False,
    ignored_file_prefixes: List[str] = IGNORED_FILE_PREFIXES,
    plain_text_output: bool = False,
    query: str = "",
) -> None:
    """
    Search all files on a given branch in the remote nf-core/testdatasets repository on github
    with an interactive autocompleting prompt and print the file matching the query.

    Specifying a branch is required. If an empty string or None is specified as a branch,
    the user is prompted to selecte a branch as well.

    The resulting file can optionally be parsed as a nextflow path or a url for downloading
    """
    branch, all_branches = get_or_prompt_branch(maybe_branch)

    stdout.print("Searching files on branch: ", branch)
    tree = list_files_by_branch(branch, all_branches, ignored_file_prefixes)
    files = sum(tree.values(), [])  # flat representation of tree

    file_selected = False

    if query:
        # Check if only one file matches the query and directly return it
        filtered_files = [f for f in files if query in f]
        if len(filtered_files) == 1:
            selection = filtered_files[0]
            file_selected = True

    while not file_selected:
        selection = questionary.autocomplete(
            "File:", choices=files, style=nfcore_question_style, default=query
        ).unsafe_ask()

        file_selected = any([selection == file for file in files])
        if not file_selected:
            stdout.print("Please select a file.")

    if generate_nf_path:
        stdout.print(create_pretty_nf_path(selection, branch == MODULES_BRANCH_NAME))
    elif generate_dl_url:
        stdout.print(create_download_url(branch, selection))
    elif plain_text_output:
        stdout.print(selection)
        stdout.print(create_pretty_nf_path(selection, branch == MODULES_BRANCH_NAME))
        stdout.print(create_download_url(branch, selection))
    else:
        table = rich.table.Table(show_header=False)
        table.add_row("File Name:", selection)
        table.add_row("Nextflow Import:", create_pretty_nf_path(selection, branch == MODULES_BRANCH_NAME))
        table.add_row("Download Link:", create_download_url(branch, selection))
        stdout.print(table)
