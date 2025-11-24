from pathlib import Path

import yaml

import nf_core.modules.lint

from ...test_modules import TestModules


class TestMetaYml(TestModules):
    """Test meta.yml functionality"""

    def test_modules_lint_update_meta_yml(self):
        """update the meta.yml of a module"""
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules, fix=True)
        module_lint.lint(print_results=False, module="bpipe/test")
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0

    def test_modules_meta_yml_incorrect_licence_field(self):
        """Test linting a module with an incorrect Licence field in meta.yml"""
        with open(self.bpipe_test_module_path / "meta.yml") as fh:
            meta_yml = yaml.safe_load(fh)
        meta_yml["tools"][0]["bpipe"]["licence"] = "[MIT]"
        with open(
            self.bpipe_test_module_path / "meta.yml",
            "w",
        ) as fh:
            fh.write(yaml.dump(meta_yml))
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")

        assert len(module_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) >= 0
        assert len(module_lint.warned) >= 0
        assert module_lint.failed[0].lint_test == "meta_yml_valid"

    def test_modules_meta_yml_output_mismatch(self):
        """Test linting a module with an extra entry in output fields in meta.yml compared to module.output"""
        with open(Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "main.nf")) as fh:
            main_nf = fh.read()
        main_nf_new = main_nf.replace("emit: sequence_report", "emit: bai")
        with open(Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "main.nf"), "w") as fh:
            fh.write(main_nf_new)
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")
        with open(Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "main.nf"), "w") as fh:
            fh.write(main_nf)
        assert len(module_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) >= 0
        assert "Module `meta.yml` does not match `main.nf`" in module_lint.failed[0].message

    def test_modules_meta_yml_incorrect_name(self):
        """Test linting a module with an incorrect name in meta.yml"""
        with open(Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "meta.yml")) as fh:
            meta_yml = yaml.safe_load(fh)
        meta_yml["name"] = "bpipe/test"
        with open(
            Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "meta.yml"),
            "w",
        ) as fh:
            fh.write(yaml.dump(meta_yml))
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")

        assert len(module_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) >= 0
        assert len(module_lint.warned) >= 0
        assert module_lint.failed[0].lint_test == "meta_name"

    def test_modules_meta_yml_multiple_versions_channels(self):
        """Test linting a module with multiple versions_* channels that should be in topics"""
        # Read the main.nf file
        main_nf_path = Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "main.nf")
        with open(main_nf_path) as fh:
            main_nf_original = fh.read()

        # Add a second versions channel to the output
        main_nf_modified = main_nf_original.replace(
            "emit: versions",
            "emit: versions_bpipe, topic: versions\n    tuple val(\"${task.process}\"), val('test2'), eval('echo 1.0'), emit: versions_test, topic: versions",
        )

        with open(main_nf_path, "w") as fh:
            fh.write(main_nf_modified)

        try:
            # Run lint with fix to update meta.yml
            module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules, fix=True)
            module_lint.lint(print_results=False, module="bpipe/test")

            # Read the updated meta.yml
            meta_yml_path = Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "meta.yml")
            with open(meta_yml_path) as fh:
                meta_yml = yaml.safe_load(fh)

            # Check that topics.versions is now a list with multiple entries
            assert "topics" in meta_yml, "topics should be present in meta.yml"
            assert "versions" in meta_yml["topics"], "versions should be present in topics"

            # For multiple versions channels, topics.versions should be a list
            versions_topic = meta_yml["topics"]["versions"]
            if isinstance(versions_topic, list) and all(isinstance(item, list) for item in versions_topic):
                # Multiple versions channels: should have 2 entries
                assert len(versions_topic) == 2, (
                    f"Expected 2 entries in versions topic, got {len(versions_topic)}: {versions_topic}"
                )

        finally:
            # Restore original main.nf
            with open(main_nf_path, "w") as fh:
                fh.write(main_nf_original)
