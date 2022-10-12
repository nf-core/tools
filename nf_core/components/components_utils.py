import logging
import os
import nf_core.utils

import questionary
import rich.prompt

log = logging.getLogger(__name__)


def get_repo_type(dir, repo_type=None, use_prompt=True):
    """
    Determine whether this is a pipeline repository or a clone of
    nf-core/modules
    """
    # Verify that the pipeline dir exists
    if dir is None or not os.path.exists(dir):
        raise UserWarning(f"Could not find directory: {dir}")

    # Try to find the root directory
    base_dir = os.path.abspath(dir)
    config_path_yml = os.path.join(base_dir, ".nf-core.yml")
    config_path_yaml = os.path.join(base_dir, ".nf-core.yaml")
    while (
        not os.path.exists(config_path_yml)
        and not os.path.exists(config_path_yaml)
        and base_dir != os.path.dirname(base_dir)
    ):
        base_dir = os.path.dirname(base_dir)
        config_path_yml = os.path.join(base_dir, ".nf-core.yml")
        config_path_yaml = os.path.join(base_dir, ".nf-core.yaml")
        # Reset dir if we found the config file (will be an absolute path)
        if os.path.exists(config_path_yml) or os.path.exists(config_path_yaml):
            dir = base_dir

    # Figure out the repository type from the .nf-core.yml config file if we can
    tools_config = nf_core.utils.load_tools_config(dir)
    repo_type = tools_config.get("repository_type", None)

    # If not set, prompt the user
    if not repo_type and use_prompt:
        log.warning("Can't find a '.nf-core.yml' file that defines 'repository_type'")
        repo_type = questionary.select(
            "Is this repository an nf-core pipeline or a fork of nf-core/modules?",
            choices=[
                {"name": "Pipeline", "value": "pipeline"},
                {"name": "nf-core/modules", "value": "modules"},
            ],
            style=nf_core.utils.nfcore_question_style,
        ).unsafe_ask()

        # Save the choice in the config file
        log.info("To avoid this prompt in the future, add the 'repository_type' key to a root '.nf-core.yml' file.")
        if rich.prompt.Confirm.ask("[bold][blue]?[/] Would you like me to add this config now?", default=True):
            with open(os.path.join(dir, ".nf-core.yml"), "a+") as fh:
                fh.write(f"repository_type: {repo_type}\n")
                log.info("Config added to '.nf-core.yml'")

    # Not set and not allowed to ask
    elif not repo_type:
        raise UserWarning("Repository type could not be established")

    # Check if it's a valid answer
    if not repo_type in ["pipeline", "modules"]:
        raise UserWarning(f"Invalid repository type: '{repo_type}'")

    # It was set on the command line, return what we were given
    return [dir, repo_type]


def get_component_dirs(self, component):
    """
    Given a directory and a tool/subtool or subworkflow name, set the file paths and check if they already exist
    Args:
        component (str): Type of component. "modules" or "subworkflows".

    Returns dict: keys are relative paths to template files, vals are target paths.
    """

    file_paths = {}

    if self.repo_type == "pipeline":
        local_component_dir = os.path.join(self.directory, component, "local")
        if component == "modules":
            component_name = self.tool_name
        elif component == "subworkflows":
            component_name = self.subworkflow_name

        # Check whether component file already exists
        component_file = os.path.join(local_component_dir, f"{component_name}.nf")
        if os.path.exists(component_file) and not self.force_overwrite:
            raise UserWarning(f"{component[:-1]} file exists already: '{component_file}'. Use '--force' to overwrite")

        # If a subtool, check if there is a module called the base tool name already
        if self.subtool and os.path.exists(os.path.join(local_modules_dir, f"{self.tool}.nf")):
            raise UserWarning(f"Module '{self.tool}' exists already, cannot make subtool '{self.tool_name}'")

        # If no subtool, check that there isn't already a tool/subtool
        tool_glob = glob.glob(f"{local_modules_dir}/{self.tool}_*.nf")
        if not self.subtool and tool_glob:
            raise UserWarning(f"Module subtool '{tool_glob[0]}' exists already, cannot make tool '{self.tool_name}'")

        # Set file paths
        file_paths[os.path.join("modules", "main.nf")] = module_file

    if self.repo_type == "modules":
        software_dir = os.path.join(self.directory, self.default_modules_path, self.tool_dir)
        test_dir = os.path.join(self.directory, self.default_tests_path, self.tool_dir)

        # Check if module directories exist already
        if os.path.exists(software_dir) and not self.force_overwrite:
            raise UserWarning(f"Module directory exists: '{software_dir}'. Use '--force' to overwrite")

        if os.path.exists(test_dir) and not self.force_overwrite:
            raise UserWarning(f"Module test directory exists: '{test_dir}'. Use '--force' to overwrite")

        # If a subtool, check if there is a module called the base tool name already
        parent_tool_main_nf = os.path.join(self.directory, self.default_modules_path, self.tool, "main.nf")
        parent_tool_test_nf = os.path.join(self.directory, self.default_tests_path, self.tool, "main.nf")
        if self.subtool and os.path.exists(parent_tool_main_nf):
            raise UserWarning(f"Module '{parent_tool_main_nf}' exists already, cannot make subtool '{self.tool_name}'")
        if self.subtool and os.path.exists(parent_tool_test_nf):
            raise UserWarning(f"Module '{parent_tool_test_nf}' exists already, cannot make subtool '{self.tool_name}'")

        # If no subtool, check that there isn't already a tool/subtool
        tool_glob = glob.glob(f"{os.path.join(self.directory, self.default_modules_path, self.tool)}/*/main.nf")
        if not self.subtool and tool_glob:
            raise UserWarning(f"Module subtool '{tool_glob[0]}' exists already, cannot make tool '{self.tool_name}'")

        # Set file paths - can be tool/ or tool/subtool/ so can't do in template directory structure
        file_paths[os.path.join("modules", "main.nf")] = os.path.join(software_dir, "main.nf")
        file_paths[os.path.join("modules", "meta.yml")] = os.path.join(software_dir, "meta.yml")
        file_paths[os.path.join("tests", "main.nf")] = os.path.join(test_dir, "main.nf")
        file_paths[os.path.join("tests", "test.yml")] = os.path.join(test_dir, "test.yml")
        file_paths[os.path.join("tests", "nextflow.config")] = os.path.join(test_dir, "nextflow.config")

    return file_paths


def get_subworkflow_dirs(self):
    """Given a directory and a subworkflow, set the file paths and check if they already exist

    Returns dict: keys are relative paths to template files, vals are target paths.
    """

    file_paths = {}

    if self.repo_type == "pipeline":
        local_subworkflow_dir = os.path.join(self.directory, "subworkflows", "local")

        # Check whether subworkflow file already exists
        subworkflow_file = os.path.join(local_subworkflow_dir, f"{self.subworkflow_name}.nf")
        if os.path.exists(subworkflow_file) and not self.force_overwrite:
            raise UserWarning(f"Subworkflow file exists already: '{subworkflow_file}'. Use '--force' to overwrite")

        # Set file paths
        file_paths[os.path.join("subworkflows", "main.nf")] = subworkflow_file

    if self.repo_type == "modules":
        subworkflow_path = os.path.join(self.directory, "subworkflows", "nf-core", self.subworkflow_dir)
        test_dir = os.path.join(self.directory, "tests", "subworkflows", "nf-core", self.subworkflow_dir)

        # Check if module directories exist already
        if os.path.exists(subworkflow_path) and not self.force_overwrite:
            raise UserWarning(f"Subworkflow directory exists: '{subworkflow_path}'. Use '--force' to overwrite")

        if os.path.exists(test_dir) and not self.force_overwrite:
            raise UserWarning(f"Subworkflow test directory exists: '{test_dir}'. Use '--force' to overwrite")

        # Set file paths
        file_paths[os.path.join("subworkflows", "main.nf")] = os.path.join(subworkflow_path, "main.nf")
        file_paths[os.path.join("subworkflows", "meta.yml")] = os.path.join(subworkflow_path, "meta.yml")
        file_paths[os.path.join("tests", "main.nf")] = os.path.join(test_dir, "main.nf")
        file_paths[os.path.join("tests", "test.yml")] = os.path.join(test_dir, "test.yml")
        file_paths[os.path.join("tests", "nextflow.config")] = os.path.join(test_dir, "nextflow.config")

    return file_paths
