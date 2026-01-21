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
            assert isinstance(versions_topic, list) and all(isinstance(item, list) for item in versions_topic)
            # Two versions channels: should have 2 entries
            assert len(versions_topic) == 2, (
                f"Expected 2 entries in versions topic, got {len(versions_topic)}: {versions_topic}"
            )

        finally:
            # Restore original main.nf
            with open(main_nf_path, "w") as fh:
                fh.write(main_nf_original)

    def test_modules_meta_yml_missing_topic_fixed(self):
        """Test that a missing topic in meta.yml is added when running lint --fix"""
        # Read the main.nf file
        main_nf_path = Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "main.nf")
        with open(main_nf_path) as fh:
            main_nf_original = fh.read()

        # Read the original meta.yml
        meta_yml_path = Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "meta.yml")
        with open(meta_yml_path) as fh:
            meta_yml_original = fh.read()

        # Add a topic to main.nf
        main_nf_modified = main_nf_original.replace("emit: sequence_report", "emit: sequence_report, topic: versions")

        with open(main_nf_path, "w") as fh:
            fh.write(main_nf_modified)

        # Remove topics from meta.yml if they exist
        with open(meta_yml_path) as fh:
            meta_yml = yaml.safe_load(fh)

        if "topics" in meta_yml:
            del meta_yml["topics"]

        with open(meta_yml_path, "w") as fh:
            fh.write(yaml.dump(meta_yml))

        try:
            # First lint without fix should fail
            module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules, fix=False)
            module_lint.lint(print_results=False, module="bpipe/test")

            # Should have failures for missing topics
            has_topic_failure = any(
                result.lint_test in ["has_meta_topics", "correct_meta_topics"] for result in module_lint.failed
            )
            assert has_topic_failure, "Expected failure for missing topics in meta.yml"

            # Now lint with fix to add the missing topic
            module_lint_fix = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules, fix=True)
            module_lint_fix.lint(print_results=False, module="bpipe/test")

            # Read the updated meta.yml
            with open(meta_yml_path) as fh:
                meta_yml_updated = yaml.safe_load(fh)

            # Check that topics section was added
            assert "topics" in meta_yml_updated, "topics should be added to meta.yml after fix"
            assert "versions" in meta_yml_updated["topics"], "reports topic should be present in meta.yml"

            # Check that the versions topic has the correct structure
            versions_topic = meta_yml_updated["topics"]["versions"]
            assert isinstance(versions_topic, list), "versions topic should be a list"
            assert len(versions_topic[0]) == 3, "versions topic should have 1 entrie with 3 elements"

        finally:
            # Restore original files
            with open(main_nf_path, "w") as fh:
                fh.write(main_nf_original)
            with open(meta_yml_path, "w") as fh:
                fh.write(meta_yml_original)

    def test_modules_meta_yml_val_topic_gets_string_type(self):
        """Test that val() keywords in topics get type: string, not type: eval"""
        # Read the main.nf file
        main_nf_path = Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "main.nf")
        with open(main_nf_path) as fh:
            main_nf_original = fh.read()

        # Read the original meta.yml
        meta_yml_path = Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "meta.yml")
        with open(meta_yml_path) as fh:
            meta_yml_original = fh.read()

        # Modify main.nf to use val() for version instead of eval()
        # This simulates a module like fastk that has hardcoded version
        import re

        main_nf_modified = re.sub(
            r'eval\("bpipe --version"\)',
            "val('1.2')",
            main_nf_original,
        )

        # Verify the replacement worked
        assert "eval" not in [line for line in main_nf_modified.split("\n") if "versions_bpipe" in line][0], (
            "Replacement failed: eval still in versions line"
        )
        assert "val('1.2')" in main_nf_modified, "Replacement failed: val('1.2') not in main.nf"

        with open(main_nf_path, "w") as fh:
            fh.write(main_nf_modified)

        try:
            # Run lint with fix to update meta.yml
            module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules, fix=True)
            module_lint.lint(print_results=False, module="bpipe/test")

            # Read the updated meta.yml
            with open(meta_yml_path) as fh:
                meta_yml = yaml.safe_load(fh)

            # Check that topics.versions exists
            assert "topics" in meta_yml, "topics should be present in meta.yml"
            assert "versions" in meta_yml["topics"], "versions should be present in topics"

            # Check the structure - should be [[{process: {}}, {tool: {}}, {version: {}}]]
            versions_topic = meta_yml["topics"]["versions"]
            assert isinstance(versions_topic, list), "versions topic should be a list"
            assert len(versions_topic) == 1, f"Expected 1 entry in versions topic, got {len(versions_topic)}"
            assert len(versions_topic[0]) == 3, f"Expected 3 elements in versions entry, got {len(versions_topic[0])}"

            # Check that the third element (version) has type: string (since it's val(), not eval())
            version_element = versions_topic[0][2]  # Third element is the version
            version_key = list(version_element.keys())[0]
            version_meta = version_element[version_key]
            assert "type" in version_meta, f"Version element should have a type field: {version_meta}"
            assert version_meta["type"] == "string", (
                f"Version element should have type: string (since it's val()), but got type: {version_meta['type']}"
            )

        finally:
            # Restore original files
            with open(main_nf_path, "w") as fh:
                fh.write(main_nf_original)
            with open(meta_yml_path, "w") as fh:
                fh.write(meta_yml_original)
