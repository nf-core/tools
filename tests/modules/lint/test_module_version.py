import nf_core.modules.lint

from ...test_modules import TestModules


class TestModuleVersion(TestModules):
    """Test module_version.py functionality"""

    def test_module_version_with_git_sha(self):
        """Test module version when git_sha is present in modules.json"""
        # Install a module
        if not self.mods_install.install("samtools/sort"):
            self.fail("Failed to install samtools/sort module - this indicates a test infrastructure problem")
        # Run lint on the module - should have a git_sha entry
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)
        module_lint.lint(print_results=False, module="samtools/sort", key=["module_version"])

        # Should pass git_sha test (git_sha entry exists)
        passed_test_names = [test.lint_test for test in module_lint.passed]
        assert "git_sha" in passed_test_names

        # Should have module_version test result (either passed or warned)
        all_test_names = [test.lint_test for test in module_lint.passed + module_lint.warned + module_lint.failed]
        assert "module_version" in all_test_names

    def test_module_version_up_to_date(self):
        """Test module version when module is up to date"""
        # Install a module
        if not self.mods_install.install("samtools/sort"):
            self.fail("Failed to install samtools/sort module - this indicates a test infrastructure problem")
        # Run lint on the module
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)
        module_lint.lint(print_results=False, module="samtools/sort", key=["module_version"])

        # Should have a result for module_version (either passed if up-to-date or warned if newer available)
        all_tests = module_lint.passed + module_lint.warned + module_lint.failed
        version_test_names = [test.lint_test for test in all_tests]
        assert "module_version" in version_test_names

    def test_module_version_outdated(self):
        """Test module version when module is outdated"""
        import json
        from pathlib import Path
        from unittest.mock import patch

        # Install a module
        if not self.mods_install.install("samtools/sort"):
            self.fail("Failed to install samtools/sort module - this indicates a test infrastructure problem")

        # Mock git log to return a newer version than what's in modules.json
        mock_git_log = [
            {"git_sha": "newer_fake_sha_123456", "date": "2024-01-01"},
            {"git_sha": "current_fake_sha_654321", "date": "2023-12-01"},
        ]

        # Modify modules.json to have an older SHA
        modules_json_path = Path(self.pipeline_dir, "modules.json")
        with open(modules_json_path) as fh:
            modules_json = json.load(fh)

        # Set module to an "older" version
        modules_json["repos"]["https://github.com/nf-core/modules.git"]["modules"]["nf-core"]["samtools/sort"][
            "git_sha"
        ] = "current_fake_sha_654321"

        with open(modules_json_path, "w") as fh:
            json.dump(modules_json, fh, indent=2)

        # Mock the git log fetch to return our fake newer version
        with patch("nf_core.modules.modules_repo.ModulesRepo.get_component_git_log", return_value=mock_git_log):
            module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)
            module_lint.lint(print_results=False, module="samtools/sort", key=["module_version"])

        # Should have warned about newer version available
        warned_test_names = [test.lint_test for test in module_lint.warned]
        assert "module_version" in warned_test_names

        # Check that the warning message indicates new version available
        version_warnings = [test for test in module_lint.warned if test.lint_test == "module_version"]
        assert len(version_warnings) > 0
        assert "New version available" in version_warnings[0].message

    def test_module_version_git_log_fail(self):
        """Test module version when git log fetch fails"""
        from unittest.mock import patch

        # Install a module
        if not self.mods_install.install("samtools/sort"):
            self.fail("Failed to install samtools/sort module - this indicates a test infrastructure problem")

        # Mock get_component_git_log to raise UserWarning (network failure, invalid repo, etc.)
        with patch(
            "nf_core.modules.modules_repo.ModulesRepo.get_component_git_log",
            side_effect=UserWarning("Failed to fetch git log"),
        ):
            module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)
            module_lint.lint(print_results=False, module="samtools/sort", key=["module_version"])

        # Should have warned about git log fetch failure
        warned_test_names = [test.lint_test for test in module_lint.warned]
        assert "module_version" in warned_test_names

        # Check that the warning message indicates git log fetch failure
        version_warnings = [test for test in module_lint.warned if test.lint_test == "module_version"]
        assert len(version_warnings) > 0
        assert "Failed to fetch git log" in version_warnings[0].message
