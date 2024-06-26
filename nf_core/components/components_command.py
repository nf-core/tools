import logging
import mmap
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union

import nf_core.utils
from nf_core.modules.modules_json import ModulesJson
from nf_core.modules.modules_repo import ModulesRepo

from .components_utils import get_repo_info

log = logging.getLogger(__name__)


class ComponentCommand:
    """
    Base class for the 'nf-core modules' and 'nf-core subworkflows' commands
    """

    def __init__(
        self,
        component_type: str,
        dir: str,
        remote_url: Optional[str] = None,
        branch: Optional[str] = None,
        no_pull: bool = False,
        hide_progress: bool = False,
        no_prompts: bool = False,
    ) -> None:
        """
        Initialise the ComponentClass object
        """
        self.component_type = component_type
        self.dir = dir
        self.modules_repo = ModulesRepo(remote_url, branch, no_pull, hide_progress)
        self.hide_progress = hide_progress
        self.no_prompts = no_prompts
        self._configure_repo_and_paths()

    def _configure_repo_and_paths(self, nf_dir_req: bool = True) -> None:
        """
        Determine the repo type and set some default paths.
        If this is a modules repo, determine the org_path too.

        Args:
            nf_dir_req (bool, optional): Whether this command requires being run in the nf-core modules repo or a nf-core pipeline repository. Defaults to True.
        """

        try:
            if self.dir:
                self.dir, self.repo_type, self.org = get_repo_info(self.dir, use_prompt=not self.no_prompts)
            else:
                self.repo_type = None
                self.org = ""
        except UserWarning:
            if nf_dir_req:
                raise
            self.repo_type = None
            self.org = ""
        self.default_modules_path = Path("modules", self.org)
        self.default_tests_path = Path("tests", "modules", self.org)
        self.default_subworkflows_path = Path("subworkflows", self.org)
        self.default_subworkflows_tests_path = Path("tests", "subworkflows", self.org)

    def get_local_components(self) -> List[str]:
        """
        Get the local modules/subworkflows in a pipeline
        """
        local_component_dir = Path(self.dir, self.component_type, "local")
        return [
            str(path.relative_to(local_component_dir)) for path in local_component_dir.iterdir() if path.suffix == ".nf"
        ]

    def get_components_clone_modules(self) -> List[str]:
        """
        Get the modules/subworkflows repository available in a clone of nf-core/modules
        """
        if self.component_type == "modules":
            component_base_path = Path(self.dir, self.default_modules_path)
        elif self.component_type == "subworkflows":
            component_base_path = Path(self.dir, self.default_subworkflows_path)
        return [
            str(Path(dir).relative_to(component_base_path))
            for dir, _, files in os.walk(component_base_path)
            if "main.nf" in files
        ]

    def has_valid_directory(self) -> bool:
        """Check that we were given a pipeline or clone of nf-core/modules"""
        if self.repo_type == "modules":
            return True
        if self.dir is None or not os.path.exists(self.dir):
            log.error(f"Could not find directory: {self.dir}")
            return False
        main_nf = os.path.join(self.dir, "main.nf")
        nf_config = os.path.join(self.dir, "nextflow.config")
        if not os.path.exists(main_nf) and not os.path.exists(nf_config):
            if Path(self.dir).resolve().parts[-1].startswith("nf-core"):
                raise UserWarning(f"Could not find a 'main.nf' or 'nextflow.config' file in '{self.dir}'")
            log.warning(f"Could not find a 'main.nf' or 'nextflow.config' file in '{self.dir}'")
        return True

    def has_modules_file(self) -> None:
        """Checks whether a module.json file has been created and creates one if it is missing"""
        modules_json_path = os.path.join(self.dir, "modules.json")
        if not os.path.exists(modules_json_path):
            log.info("Creating missing 'module.json' file.")
            ModulesJson(self.dir).create()

    def clear_component_dir(self, component_name: str, component_dir: str) -> bool:
        """
        Removes all files in the module/subworkflow directory

        Args:
            component_name (str): The name of the module/subworkflow
            component_dir (str): The path to the module/subworkflow in the module repository

        """

        try:
            shutil.rmtree(component_dir)
            # remove all empty directories
            for dir_path, dir_names, filenames in os.walk(self.dir, topdown=False):
                if not dir_names and not filenames:
                    try:
                        os.rmdir(dir_path)
                    except OSError:
                        pass
                    else:
                        log.debug(f"Deleted  directory: '{dir_path}'")

            log.debug(f"Successfully removed {self.component_type[:-1]} {component_name}")
            return True
        except OSError as e:
            log.error(f"Could not remove {self.component_type[:-1]} {component_name}: {e}")
            return False

    def components_from_repo(self, install_dir: str) -> List[str]:
        """
        Gets the modules/subworkflows installed from a certain repository

        Args:
            install_dir (str): The name of the directory where modules/subworkflows are installed

        Returns:
            [str]: The names of the modules/subworkflows
        """
        repo_dir = Path(self.dir, self.component_type, install_dir)
        if not repo_dir.exists():
            raise LookupError(f"Nothing installed from {install_dir} in pipeline")

        return [
            str(Path(dir_path).relative_to(repo_dir)) for dir_path, _, files in os.walk(repo_dir) if "main.nf" in files
        ]

    def install_component_files(
        self, component_name: str, component_version: str, modules_repo: ModulesRepo, install_dir: str
    ) -> bool:
        """
        Installs a module/subworkflow into the given directory

        Args:
            component_name (str): The name of the module/subworkflow
            component_version (str): Git SHA for the version of the module/subworkflow to be installed
            modules_repo (ModulesRepo): A correctly configured ModulesRepo object
            install_dir (str): The path to where the module/subworkflow should be installed (should be the 'modules/' or 'subworkflows/' dir of the pipeline)

        Returns:
            (bool): Whether the operation was successful of not
        """
        return modules_repo.install_component(component_name, install_dir, component_version, self.component_type)

    def load_lint_config(self) -> None:
        """Parse a pipeline lint config file.

        Load the '.nf-core.yml'  config file and extract
        the lint config from it

        Add parsed config to the `self.lint_config` class attribute.
        """
        _, tools_config = nf_core.utils.load_tools_config(self.dir)
        self.lint_config = tools_config.get("lint", {})

    def check_modules_structure(self) -> None:
        """
        Check that the structure of the modules directory in a pipeline is the correct one:
            modules/nf-core/TOOL/SUBTOOL

        Prior to nf-core/tools release 2.6 the directory structure had an additional level of nesting:
            modules/nf-core/modules/TOOL/SUBTOOL
        """
        if self.repo_type == "pipeline":
            wrong_location_modules: List[Path] = []
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
                    shutil.move(str(wrong_dir), str(correct_dir))
                    log.info(f"Moved {wrong_dir} to {correct_dir}.")
                shutil.rmtree(Path(self.dir, "modules", self.modules_repo.repo_path, "modules"))
                # Regenerate modules.json file
                modules_json = ModulesJson(self.dir)
                modules_json.check_up_to_date()

    def check_patch_paths(self, patch_path: Path, module_name: str) -> None:
        """
        Check that paths in patch files are updated to the new modules path
        """
        if patch_path.exists():
            log.info(f"Modules {module_name} contains a patch file.")
            rewrite = False
            with open(patch_path) as fh:
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
                if modules_json.has_git_url_and_modules() and modules_json.modules_json is not None:
                    modules_json.modules_json["repos"][self.modules_repo.remote_url]["modules"][
                        self.modules_repo.repo_path
                    ][module_name]["patch"] = str(patch_path.relative_to(Path(self.dir).resolve()))
                modules_json.dump()

    def check_if_in_include_stmts(self, component_path: str) -> Dict[str, List[Dict[str, Union[int, str]]]]:
        """
        Checks for include statements in the main.nf file of the pipeline and a list of line numbers where the component is included
        Args:
            component_path (str): The path to the module/subworkflow

        Returns:
            (list): A list of dictionaries, with the workflow file and the line number where the component is included
        """
        include_stmts: Dict[str, List[Dict[str, Union[int, str]]]] = {}
        if self.repo_type == "pipeline":
            workflow_files = Path(self.dir, "workflows").glob("*.nf")
            for workflow_file in workflow_files:
                with open(workflow_file) as fh:
                    # Check if component path is in the file using mmap
                    with mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as s:
                        if s.find(component_path.encode()) != -1:
                            # If the component path is in the file, check for include statements
                            for i, line in enumerate(fh):
                                if line.startswith("include") and component_path in line:
                                    if str(workflow_file) not in include_stmts:
                                        include_stmts[str(workflow_file)] = []
                                    include_stmts[str(workflow_file)].append(
                                        {"line_number": i + 1, "line": line.rstrip()}
                                    )

            return include_stmts
        else:
            log.debug("Not a pipeline repository, skipping check for include statements")
            return include_stmts
