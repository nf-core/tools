import json
import logging
import os

import rich

import nf_core.modules.module_utils
from nf_core.modules.modules_json import ModulesJson
from nf_core.modules.modules_repo import NF_CORE_MODULES_NAME, ModulesRepo

log = logging.getLogger(__name__)


class SubworkflowList(object):
    def __init__(self, pipeline_dir, remote=True, remote_url=None, branch=None, no_pull=False):
        # super().__init__(pipeline_dir, remote_url, branch, no_pull)
        self.dir = pipeline_dir
        self.remote = remote
        self.modules_repo = ModulesRepo(remote_url, branch, no_pull)
        try:
            if self.dir:
                self.dir, self.repo_type = nf_core.modules.module_utils.get_repo_type(self.dir)
            else:
                self.repo_type = None
        except LookupError as e:
            raise UserWarning(e)

    def list_subworkflows(self, keywords=None, print_json=False):
        """
        Get available subworkflows names from GitHub tree for repo
        and print as list to stdout
        """

        # Initialise rich table
        table = rich.table.Table()
        table.add_column("Subworkflow Name")
        subworkflows = []

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

            # Filter the subworkflows by keywords
            subworkflows = [
                swf for swf in self.modules_repo.get_avail_subworkflows() if all(k in swf for k in keywords)
            ]

            # Nothing found
            if len(subworkflows) == 0:
                log.info(
                    f"No available subworkflows found in {self.modules_repo.remote_url} ({self.modules_repo.branch})"
                    f"{pattern_msg(keywords)}"
                )
                return ""

            for swf in sorted(subworkflows):
                table.add_row(swf)

        # We have a pipeline - list what's installed
        else:
            # Check that we are in a pipeline directory
            try:
                _, repo_type = nf_core.modules.module_utils.get_repo_type(self.dir)
                if repo_type != "pipeline":
                    raise UserWarning(
                        "The command 'nf-core subworkflows list local' must be run from a pipeline directory.",
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
            repos_with_swfs = {
                repo_url: [swf for swf in subworkflows if all(k in swf[1] for k in keywords)]
                for repo_url, subworkflows in modules_json.get_installed_subworkflows().items()
            }

            # Nothing found
            if sum(map(len, repos_with_swfs)) == 0:
                log.info(f"No nf-core subworkflows found in '{self.dir}'{pattern_msg(keywords)}")
                return ""

            table.add_column("Repository")
            table.add_column("Version SHA")
            table.add_column("Message")
            table.add_column("Date")

            # Load 'modules.json'
            modules_json = modules_json.modules_json

            for repo_url, subworkflow_with_dir in sorted(repos_with_swfs.items()):
                repo_entry = modules_json["repos"].get(repo_url, {})
                for install_dir, subworkflow in sorted(subworkflow_with_dir):
                    repo_modules = repo_entry.get("subworkflows")
                    subworkflow_entry = repo_modules.get(install_dir).get(subworkflow)

                    if subworkflow_entry:
                        version_sha = subworkflow_entry["git_sha"]
                        try:
                            # pass repo_name to get info on modules even outside nf-core/modules
                            message, date = ModulesRepo(
                                remote_url=repo_url,
                                branch=subworkflow_entry["branch"],
                            ).get_commit_info(version_sha)
                        except LookupError as e:
                            log.warning(e)
                            date = "[red]Not Available"
                            message = "[red]Not Available"
                    else:
                        log.warning(
                            f"Commit SHA for subworkflow '{install_dir}/{subworkflow}' is missing from 'modules.json'"
                        )
                        version_sha = "[red]Not Available"
                        date = "[red]Not Available"
                        message = "[red]Not Available"
                    table.add_row(subworkflow, repo_url, version_sha, message, date)

        if print_json:
            return json.dumps(subworkflows, sort_keys=True, indent=4)

        if self.remote:
            log.info(
                f"Subworkflows available from {self.modules_repo.remote_url} ({self.modules_repo.branch})"
                f"{pattern_msg(keywords)}:\n"
            )
        else:
            log.info(f"Subworkflows installed in '{self.dir}'{pattern_msg(keywords)}:\n")
        return table

    def has_valid_directory(self):
        """Check that we were given a pipeline"""
        if self.dir is None or not os.path.exists(self.dir):
            log.error(f"Could not find pipeline: {self.dir}")
            return False
        main_nf = os.path.join(self.dir, "main.nf")
        nf_config = os.path.join(self.dir, "nextflow.config")
        if not os.path.exists(main_nf) and not os.path.exists(nf_config):
            raise UserWarning(f"Could not find a 'main.nf' or 'nextflow.config' file in '{self.dir}'")
        return True
