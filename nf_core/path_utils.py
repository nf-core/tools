from pathlib import Path


def root_stripper(func):
    def wrapper(self, *args, **kwargs):
        no_root = kwargs.pop("no_root", None)
        p = func(self, *args, **kwargs)
        if no_root:
            p = p.relative_to(self.dir)
        return p

    return wrapper


class NFCorePaths:
    def __init__(self, root_dir, org):
        self.dir = Path(root_dir)
        self.org = org

    def get_path(self, path):
        return Path(self.dir, path)

    @root_stripper
    def get_component_path(self, component):
        return self.get_path(Path(component, self.org))

    @root_stripper
    def get_component_tests_path(self, component):
        return self.get_path(Path("tests", component, self.org))

    @root_stripper
    def get_modules_path(self):
        return self.get_component_path("modules")

    @root_stripper
    def get_modules_tests_path(self):
        return self.get_component_tests_path("modules")

    @root_stripper
    def get_subworkflows_path(self):
        return self.get_component_path("subworkflows")

    @root_stripper
    def get_subworkflows_tests_path(self):
        return self.get_component_tests_path("subworkflows")

    @root_stripper
    def get_modules_json(self):
        return self.get_path("modules.json")

    @root_stripper
    def get_main_nf(self):
        return self.get_path("main.nf")

    @root_stripper
    def get_nf_config(self):
        return self.get_path("nextflow.config")

    @root_stripper
    def get_nf_core_config_yml(self):
        return self.get_path(".nf-core.yml")

    @root_stripper
    def get_nf_core_config_yaml(self):
        return self.get_path(".nf-core.yaml")

    @root_stripper
    def get_nf_core_lint_yml(self):
        return self.get_path(".nf-core-lint.yml")

    @root_stripper
    def get_nf_core_lint_yaml(self):
        return self.get_path(".nf-core-lint.yaml")
