import os
import requests
import rich
from nf_core.modules.lint import LintResult

def module_changes(self, nfcore_modules):
    """
    Checks whether installed nf-core modules have changed compared to the
    original repository
    Downloads the 'main.nf', 'functions.nf' and 'meta.yml' files for every module
    and compare them to the local copies
    """
    files_to_check = ["main.nf", "functions.nf", "meta.yml"]

    progress_bar = rich.progress.Progress(
        "[bold blue]{task.description}",
        rich.progress.BarColumn(bar_width=None),
        "[magenta]{task.completed} of {task.total}[reset] » [bold yellow]{task.fields[test_name]}",
        transient=True,
    )
    with progress_bar:
        comparison_progress = progress_bar.add_task(
            "Comparing local file to remote", total=len(nfcore_modules), test_name=nfcore_modules[0].module_name
        )
        # Loop over nf-core modules
        for mod in nfcore_modules:
            progress_bar.update(comparison_progress, advance=1, test_name=mod.module_name)
            module_base_url = f"https://raw.githubusercontent.com/{self.modules_repo.name}/{self.modules_repo.branch}/software/{mod.module_name}/"

            for f in files_to_check:
                # open local copy, continue if file not found (a failed message has already been issued in this case)
                try:
                    local_copy = open(os.path.join(mod.module_dir, f), "r").read()
                except FileNotFoundError as e:
                    continue

                # Download remote copy and compare
                url = module_base_url + f
                r = requests.get(url=url)

                if r.status_code != 200:
                    self.warned.append(
                        LintResult(
                            mod,
                            "check_local_copy",
                            f"Could not fetch remote copy, skipping comparison.",
                            f"{os.path.join(mod.module_dir, f)}",
                        )
                    )
                else:
                    try:
                        remote_copy = r.content.decode("utf-8")

                        if local_copy != remote_copy:
                            self.warned.append(
                                LintResult(
                                    mod,
                                    "check_local_copy",
                                    "Local copy of module outdated",
                                    f"{os.path.join(mod.module_dir, f)}",
                                )
                            )
                        else:
                            self.passed.append(
                                LintResult(
                                    mod,
                                    "check_local_copy",
                                    "Local copy of module up to date",
                                    f"{os.path.join(mod.module_dir, f)}",
                                )
                            )
                    except UnicodeDecodeError as e:
                        self.warned.append(
                            LintResult(
                                mod,
                                "check_local_copy",
                                f"Could not decode file from {url}. Skipping comparison ({e})",
                                f"{os.path.join(mod.module_dir, f)}",
                            )
                        )