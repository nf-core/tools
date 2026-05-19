from pathlib import Path

from nf_core.modules.modules_json import ModulesJson, ModulesJsonType


def modules_json(self) -> dict[str, list[str]]:
    """Make sure all modules described in the ``modules.json`` file are actually installed

    Every module installed from ``nf-core/modules`` must have an entry in the ``modules.json`` file
    with an associated version commit hash.

    * Failure: If module entries are found in ``modules.json`` for modules that are not installed
    """
    passed = []
    warned = []
    failed = []

    # Load pipeline modules and modules.json
    _modules_json = ModulesJson(self.wf_path)
    _modules_json.load()
    modules_json_dict: ModulesJsonType | None = _modules_json.modules_json
    modules_dir = Path(self.wf_path, "modules")

    if _modules_json and modules_json_dict is not None:
        all_modules_passed = True

        for repo in modules_json_dict["repos"]:
            if not repo.startswith("http"):
                failed.append(f'Repository link for {repo} doesn\'t start with "http" in `modules.json`.')

            if "modules" in modules_json_dict["repos"][repo]:
                # Module linting
                for install_dir in modules_json_dict["repos"][repo]["modules"]:
                    for module, module_entry in modules_json_dict["repos"][repo]["modules"][install_dir].items():
                        if not Path(modules_dir, install_dir, module).exists():
                            failed.append(
                                f"Entry for `{Path(modules_dir, install_dir, module)}` found in `modules.json` but module is not installed in "
                                "pipeline."
                            )
                            all_modules_passed = False
                        if module_entry.get("branch") is None:
                            failed.append(
                                f"Entry for `{Path(modules_dir, install_dir, module)}` is missing branch information."
                            )
                        if module_entry.get("git_sha") is None:
                            failed.append(
                                f"Entry for `{Path(modules_dir, install_dir, module)}` is missing version information."
                            )
                if all_modules_passed:
                    passed.append("Only installed modules found in `modules.json`")

            if not any(component in modules_json_dict["repos"][repo] for component in ["modules", "subworkflows"]):
                failed.append(f"No modules or subworkflows installed for {repo} in `modules.json`.")
    else:
        warned.append("Could not open `modules.json` file.")

    return {"passed": passed, "warned": warned, "failed": failed}
