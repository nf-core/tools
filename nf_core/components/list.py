import json
import logging

import rich

from nf_core.components.components_command import ComponentCommand
from nf_core.modules.modules_json import ModulesJson
from nf_core.modules.modules_repo import ModulesRepo

log = logging.getLogger(__name__)


class ComponentList(ComponentCommand):
    def __init__(self, component_type, pipeline_dir, remote=True, remote_url=None, branch=None, no_pull=False):
        super().__init__(component_type, pipeline_dir, remote_url, branch, no_pull)
        self.remote = remote

    def list_components(self, keywords=None, print_json=False):
        keywords = keywords or []
        """
        Get available modules/subworkflows names from GitHub tree for repo
        and print as list to stdout
        """
        # Check modules directory structure
        # self.check_component_structure(self.component_type)

        # Initialise rich table
        table = rich.table.Table()
        table.add_column(f"{self.component_type[:-1].capitalize()} Name")
        components = []

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
            # Filter the modules/subworkflows by keywords
            components = [
                comp
                for comp in self.modules_repo.get_avail_components(self.component_type)
                if all(k in comp for k in keywords)
            ]

            # Nothing found
            if len(components) == 0:
                log.info(
                    f"No available {self.component_type} found in {self.modules_repo.remote_url} ({self.modules_repo.branch})"
                    f"{pattern_msg(keywords)}"
                )
                return ""

            for comp in sorted(components):
                table.add_row(comp)

        # We have a pipeline - list what's installed
        else:
            # Check that we are in a pipeline directory

            try:
                if self.repo_type != "pipeline":
                    raise UserWarning(
                        f"The command 'nf-core {self.component_type} list local' must be run from a pipeline directory.",
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
            repos_with_comps = {
                repo_url: [comp for comp in components if all(k in comp[1] for k in keywords)]
                for repo_url, components in modules_json.get_all_components(self.component_type).items()
            }

            # Nothing found
            if sum(map(len, repos_with_comps)) == 0:
                log.info(f"No nf-core {self.component_type} found in '{self.dir}'{pattern_msg(keywords)}")
                return ""

            table.add_column("Repository")
            table.add_column("Version SHA")
            table.add_column("Message")
            table.add_column("Date")

            # Load 'modules.json'
            modules_json = modules_json.modules_json

            for repo_url, component_with_dir in sorted(repos_with_comps.items()):
                repo_entry = modules_json["repos"].get(repo_url, {})
                for install_dir, component in sorted(component_with_dir):
                    repo_modules = repo_entry.get(self.component_type)
                    component_entry = repo_modules.get(install_dir).get(component)

                    if component_entry:
                        version_sha = component_entry["git_sha"]
                        try:
                            # pass repo_name to get info on modules even outside nf-core/modules
                            message, date = ModulesRepo(
                                remote_url=repo_url,
                                branch=component_entry["branch"],
                            ).get_commit_info(version_sha)
                        except LookupError as e:
                            log.warning(e)
                            date = "[red]Not Available"
                            message = "[red]Not Available"
                    else:
                        log.warning(
                            f"Commit SHA for {self.component_type[:-1]} '{install_dir}/{self.component_type}' is missing from 'modules.json'"
                        )
                        version_sha = "[red]Not Available"
                        date = "[red]Not Available"
                        message = "[red]Not Available"
                    table.add_row(component, repo_url, version_sha, message, date)

        if print_json:
            return json.dumps(components, sort_keys=True, indent=4)

        if self.remote:
            log.info(
                f"{self.component_type.capitalize()} available from {self.modules_repo.remote_url} ({self.modules_repo.branch})"
                f"{pattern_msg(keywords)}:\n"
            )
        else:
            log.info(f"{self.component_type.capitalize()} installed in '{self.dir}'{pattern_msg(keywords)}:\n")
        return table
