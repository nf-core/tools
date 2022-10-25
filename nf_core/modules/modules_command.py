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

    def check_modules_structure(self):
        """
        Check that the structure of the modules directory in a pipeline is the correct one:
            modules/nf-core/TOOL/SUBTOOL

        Prior to nf-core/tools release 2.6 the directory structure had an additional level of nesting:
            modules/nf-core/modules/TOOL/SUBTOOL
        """
        if self.repo_type == "pipeline":
            wrong_location_modules = []
            for directory, _, files in os.walk(Path(self.dir, "modules")):
                if "main.nf" in files:
                    module_path = Path(directory).relative_to(Path(self.dir, "modules"))
                    parts = module_path.parts
                    # Check that there are modules installed directly under the 'modules' directory
                    if parts[1] == "modules":
                        wrong_location_modules.append(module_path)
            # If there are modules installed in the wrong location
            if len(wrong_location_modules) > 0:
                log.info("The modules folder structure is outdated. Reinstalling modules.")
                # Remove the local copy of the modules repository
                log.info(f"Updating '{self.modules_repo.local_repo_dir}'")
                self.modules_repo.setup_local_repo(
                    self.modules_repo.remote_url, self.modules_repo.branch, self.hide_progress
                )
                # Move wrong modules to the right directory
                for module in wrong_location_modules:
                    modules_dir = Path("modules").resolve()
                    correct_dir = Path(modules_dir, self.modules_repo.repo_path, Path(*module.parts[2:]))
                    wrong_dir = Path(modules_dir, module)
                    shutil.move(wrong_dir, correct_dir)
                    log.info(f"Moved {wrong_dir} to {correct_dir}.")
                shutil.rmtree(Path(self.dir, "modules", self.modules_repo.repo_path, "modules"))
                # Regenerate modules.json file
                modules_json = ModulesJson(self.dir)
                modules_json.check_up_to_date()
