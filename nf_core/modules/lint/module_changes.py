"""
Check whether the content of a module has changed compared to the original repository
"""
import os
import requests


def module_changes(module_lint_object, module):
    """
    Checks whether installed nf-core modules have changed compared to the
    original repository

    Downloads the ``main.nf`` and ``meta.yml`` files for every module
    and compares them to the local copies

    If the module has a commit SHA entry in the ``modules.json``, the file content is
    compared against the files in the remote at this SHA.

    Only runs when linting a pipeline, not the modules repository
    """
    files_to_check = ["main.nf", "meta.yml"]

    # Loop over nf-core modules
    module_base_url = f"https://raw.githubusercontent.com/{module_lint_object.modules_repo.name}/{module_lint_object.modules_repo.branch}/modules/{module.module_name}/"

    # If module.git_sha specified, check specific commit version for changes
    if module.git_sha:
        module_base_url = f"https://raw.githubusercontent.com/{module_lint_object.modules_repo.name}/{module.git_sha}/modules/{module.module_name}/"

    for f in files_to_check:
        # open local copy, continue if file not found (a failed message has already been issued in this case)
        try:
            local_copy = open(os.path.join(module.module_dir, f), "r").read()
        except FileNotFoundError as e:
            continue

        # Download remote copy and compare
        url = module_base_url + f
        r = requests.get(url=url)

        if r.status_code != 200:
            module.warned.append(
                (
                    "check_local_copy",
                    f"Could not fetch remote copy, skipping comparison.",
                    f"{os.path.join(module.module_dir, f)}",
                )
            )
        else:
            try:
                remote_copy = r.content.decode("utf-8")

                if local_copy != remote_copy:
                    module.failed.append(
                        (
                            "check_local_copy",
                            "Local copy of module does not match remote",
                            f"{os.path.join(module.module_dir, f)}",
                        )
                    )
                else:
                    module.passed.append(
                        (
                            "check_local_copy",
                            "Local copy of module up to date",
                            f"{os.path.join(module.module_dir, f)}",
                        )
                    )
            except UnicodeDecodeError as e:
                module.warned.append(
                    (
                        "check_local_copy",
                        f"Could not decode file from {url}. Skipping comparison ({e})",
                        f"{os.path.join(module.module_dir, f)}",
                    )
                )
