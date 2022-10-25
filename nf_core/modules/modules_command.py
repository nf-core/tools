import logging
from pathlib import Path

from nf_core.components.components_command import ComponentCommand
from nf_core.modules.modules_json import ModulesJson

log = logging.getLogger(__name__)


class ModuleCommand(ComponentCommand):
    """
    Base class for the 'nf-core modules' commands
    """

    def __init__(self, dir, remote_url=None, branch=None, no_pull=False, hide_progress=False):
        super().__init__("modules", dir, remote_url, branch, no_pull, hide_progress)

    def check_patch_paths(self, patch_path, module_name):
        """
        Check that paths in patch files are updated to the new modules path
        """
        if patch_path.exists():
            log.info(f"Modules {module_name} contains a patch file.")
            rewrite = False
            with open(patch_path, "r") as fh:
                lines = fh.readlines()
                for index, line in enumerate(lines):
                    # Check if there are old paths in the patch file and replace
                    if f"modules/{self.modules_repo.repo_path}/modules/{module_name}/" in line:
                        rewrite = True
                        lines[index] = line.replace(
                            f"modules/{self.modules_repo.repo_path}/modules/{module_name}/",
                            f"modules/{self.modules_repo.repo_path}/{module_name}/",
                        )
            if rewrite:
                log.info(f"Updating paths in {patch_path}")
                with open(patch_path, "w") as fh:
                    for line in lines:
                        fh.write(line)
                # Update path in modules.json if the file is in the correct format
                modules_json = ModulesJson(self.dir)
                modules_json.load()
                if modules_json.has_git_url_and_modules():
                    modules_json.modules_json["repos"][self.modules_repo.remote_url]["modules"][
                        self.modules_repo.repo_path
                    ][module_name]["patch"] = str(patch_path.relative_to(Path(self.dir).resolve()))
                modules_json.dump()
