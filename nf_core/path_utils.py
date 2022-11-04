from pathlib import Path


class NFCorePaths:
    def __init__(self, root_dir, org):
        self.dir = Path(root_dir or "")
        self.org = org

    def get_path(self, path):
        return Path(self.dir, path)

    def get_component_path(self, component):
        return self.get_path(Path(component, self.org))

    def get_component_tests_path(self, component):
        return self.get_path(Path("tests", component, self.org))

    def get_modules_path(self):
        return self.get_component_path("modules")

    def get_modules_tests_path(self):
        return self.get_component_tests_path("modules")

    def get_subworkflows_path(self):
        return self.get_component_path("subworkflows")

    def get_subworkflows_tests_path(self):
        return self.get_component_tests_path("subworkflows")

    def get_modules_json(self):
        return self.get_path("modules.json")

    def get_main_nf(self):
        return self.get_path("main.nf")

    def get_nf_config(self):
        return self.get_path("nextflow.config")

    def get_nf_core_config_yml(self):
        return self.get_path(".nf-core.yml")

    def get_nf_core_config_yaml(self):
        return self.get_path(".nf-core.yaml")

    def get_nf_core_lint_yml(self):
        return self.get_path(".nf-core-lint.yml")

    def get_nf_core_lint_yaml(self):
        return self.get_path(".nf-core-lint.yaml")
