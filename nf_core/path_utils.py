import os


class NFCorePaths:
    def __init__(self, root_dir, org):
        self.dir = root_dir or ""
        self.org = org

    def get_component_path(self, component):
        return os.path.join(self.dir, component, self.org)

    def get_component_tests_path(self, component):
        return os.path.join(self.dir, "tests", component, self.org)

    def get_modules_path(self):
        return self.get_component_path("modules")

    def get_modules_tests_path(self):
        return self.get_component_tests_path("modules")

    def get_subworkflows_path(self):
        return self.get_component_path("subworkflows")

    def get_subworkflows_tests_path(self):
        return self.get_component_tests_path("subworkflows")

    def get_modules_json(self):
        return os.path.join(self.dir, "modules.json")

    def get_main_nf(self):
        return os.path.join(self.dir, "main.nf")

    def get_nf_config(self):
        return os.path.join(self.dir, "nextflow.config")

    def get_nf_core_config_yml(self):
        return os.path.join(self.dir, ".nf-core.yml")

    def get_nf_core_config_yaml(self):
        return os.path.join(self.dir, ".nf-core.yaml")

    def get_nf_core_lint_yml(self):
        return os.path.join(self.dir, ".nf-core-lint.yml")

    def get_nf_core_lint_yaml(self):
        return os.path.join(self.dir, ".nf-core-lint.yaml")
