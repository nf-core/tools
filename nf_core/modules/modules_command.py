import os
import glob
import shutil
import json
import logging
import questionary


from .modules_repo import ModulesRepo
from .module_utils import create_modules_json

log = logging.getLogger(__name__)


class ModuleCommand:
    """
    Base class for the 'nf-core modules' commands
    """

    def __init__(self, pipeline_dir):
        """
        Initialise the ModulesCommand object
        """
        self.modules_repo = ModulesRepo()
        self.pipeline_dir = pipeline_dir
        self.pipeline_module_names = []

    def get_pipeline_modules(self):
        """Get list of modules installed in the current pipeline"""
        self.pipeline_module_names = []
        module_mains = glob.glob(f"{self.pipeline_dir}/modules/nf-core/software/**/main.nf", recursive=True)
        for mod in module_mains:
            self.pipeline_module_names.append(
                os.path.dirname(os.path.relpath(mod, f"{self.pipeline_dir}/modules/nf-core/software/"))
            )

    def has_valid_pipeline(self):
        """Check that we were given a pipeline"""
        if self.pipeline_dir is None or not os.path.exists(self.pipeline_dir):
            log.error("Could not find pipeline: {}".format(self.pipeline_dir))
            return False
        main_nf = os.path.join(self.pipeline_dir, "main.nf")
        nf_config = os.path.join(self.pipeline_dir, "nextflow.config")
        if not os.path.exists(main_nf) and not os.path.exists(nf_config):
            raise UserWarning(f"Could not find a 'main.nf' or 'nextflow.config' file in '{self.pipeline_dir}'")
        self.has_modules_file()
        return True

    def has_modules_file(self):
        """Checks whether a module.json file has been created and creates one if it is missing"""
        modules_json_path = os.path.join(self.pipeline_dir, "modules.json")
        if not os.path.exists(modules_json_path):
            log.info("Creating missing 'module.json' file.")
            create_modules_json(self.pipeline_dir)

    def clear_module_dir(self, module_name, module_dir):
        """Removes all files in the module directory"""
        try:
            shutil.rmtree(module_dir)
            # Try cleaning up empty parent if tool/subtool and tool/ is empty
            if module_name.count("/") > 0:
                parent_dir = os.path.dirname(module_dir)
                try:
                    os.rmdir(parent_dir)
                except OSError:
                    log.debug(f"Parent directory not empty: '{parent_dir}'")
                else:
                    log.debug(f"Deleted orphan tool directory: '{parent_dir}'")
            log.debug("Successfully removed {} module".format(module_name))
            return True
        except OSError as e:
            log.error("Could not remove module: {}".format(e))
            return False

    def download_module_file(self, module_name, module_version, install_folder, module_dir):
        """Downloads the files of a module from the remote repo"""
        files = self.modules_repo.get_module_file_urls(module_name, module_version)
        log.debug("Fetching module files:\n - {}".format("\n - ".join(files.keys())))
        for filename, api_url in files.items():
            split_filename = filename.split("/")
            dl_filename = os.path.join(self.pipeline_dir, "modules", *install_folder, *split_filename[1:])
            try:
                self.modules_repo.download_gh_file(dl_filename, api_url)
            except SystemError as e:
                log.error(e)
                return False
        log.info("Downloaded {} files to {}".format(len(files), module_dir))
        return True

    def update_modules_json(self, modules_json, modules_json_path, module_name, module_version):
        """Updates the 'module.json' file with new module info"""
        modules_json["modules"][module_name] = {"git_sha": module_version}
        with open(modules_json_path, "w") as fh:
            json.dump(modules_json, fh, indent=4)
