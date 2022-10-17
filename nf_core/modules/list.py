import json
import logging

import rich

import nf_core.modules.module_utils

from .modules_command import ModuleCommand
from .modules_json import ModulesJson
from .modules_repo import ModulesRepo

log = logging.getLogger(__name__)


class ModuleList(ModuleCommand):
    def __init__(self, pipeline_dir, remote=True, remote_url=None, branch=None, no_pull=False):
        super().__init__(pipeline_dir, remote_url, branch, no_pull)
        self.remote = remote

    def list_modules(self, keywords=None, print_json=False):
        """
        Get available module names from GitHub tree for repo
        and print as list to stdout
        """
        # Check modules directory structure
        self.check_modules_structure()

        # Initialise rich table
        table = rich.table.Table()
        table.add_column("Module Name")
        modules = []

        if keywords is None:
            keywords = []

        def pattern_msg(keywords):
            if len(keywords) == 0:
                return ""
            if len(keywords) == 1:
                return f" matching pattern '{keywords[0]}'"
            else:
                quoted_keywords = (f"'{key}'" for key in keywords)
                return f" matching patterns {', '.join(quoted_keywords)}"

        # No pipeline given - show all remote
        if self.remote:

            # Filter the modules by keywords
            modules = [mod for mod in self.modules_repo.get_avail_modules() if all(k in mod for k in keywords)]

            # Nothing found
            if len(modules) == 0:
                log.info(
                    f"No available modules found in {self.modules_repo.remote_url} ({self.modules_repo.branch})"
                    f"{pattern_msg(keywords)}"
                )
                return ""

            for mod in sorted(modules):
                table.add_row(mod)

        # We have a pipeline - list what's installed
        else:
            # Check that we are in a pipeline directory
            try:
                _, repo_type = nf_core.modules.module_utils.get_repo_type(self.dir)
                if repo_type != "pipeline":
                    raise UserWarning(
                        "The command 'nf-core modules list local' must be run from a pipeline directory.",
                    )
            except UserWarning as e:
                log.error(e)
                return ""
            # Check whether pipelines is valid
            try:
                self.has_valid_directory()
            except UserWarning as e:
                log.error(e)
                return ""

            # Verify that 'modules.json' is consistent with the installed modules
            modules_json = ModulesJson(self.dir)
            modules_json.check_up_to_date()

            # Filter by keywords
            repos_with_mods = {
                repo_url: [mod for mod in modules if all(k in mod[1] for k in keywords)]
                for repo_url, modules in modules_json.get_all_modules().items()
            }

            # Nothing found
            if sum(map(len, repos_with_mods)) == 0:
                log.info(f"No nf-core modules found in '{self.dir}'{pattern_msg(keywords)}")
                return ""

            table.add_column("Repository")
            table.add_column("Version SHA")
            table.add_column("Message")
            table.add_column("Date")

            # Load 'modules.json'
            modules_json = modules_json.modules_json

            for repo_url, module_with_dir in sorted(repos_with_mods.items()):
                repo_entry = modules_json["repos"].get(repo_url, {})
                for install_dir, module in sorted(module_with_dir):
                    repo_modules = repo_entry.get("modules")
                    module_entry = repo_modules.get(install_dir).get(module)

                    if module_entry:
                        version_sha = module_entry["git_sha"]
                        try:
                            # pass repo_name to get info on modules even outside nf-core/modules
                            message, date = ModulesRepo(
                                remote_url=repo_url,
                                branch=module_entry["branch"],
                            ).get_commit_info(version_sha)
                        except LookupError as e:
                            log.warning(e)
                            date = "[red]Not Available"
                            message = "[red]Not Available"
                    else:
                        log.warning(f"Commit SHA for module '{install_dir}/{module}' is missing from 'modules.json'")
                        version_sha = "[red]Not Available"
                        date = "[red]Not Available"
                        message = "[red]Not Available"
                    table.add_row(module, repo_url, version_sha, message, date)

        if print_json:
            return json.dumps(modules, sort_keys=True, indent=4)

        if self.remote:
            log.info(
                f"Modules available from {self.modules_repo.remote_url} ({self.modules_repo.branch})"
                f"{pattern_msg(keywords)}:\n"
            )
        else:
            log.info(f"Modules installed in '{self.dir}'{pattern_msg(keywords)}:\n")
        return table
