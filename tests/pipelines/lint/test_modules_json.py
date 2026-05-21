import json

from nf_core.modules.modules_json import (
    ModulesJson,
    ModulesJsonType,
)

from ..test_lint import TestLint


class TestLintModulesJson(TestLint):
    def setUp(self) -> None:
        super().setUp()
        self._modules_json_object: ModulesJson = ModulesJson(self.pipeline_dir)
        self._modules_json_object.load()
        self.modules_json_path = self._modules_json_object.modules_json_path
        assert self._modules_json_object.modules_json is not None
        self.modules_json: ModulesJsonType = self._modules_json_object.modules_json

    def _update_modules_json(self, new_modules_json) -> None:
        # Update modules_json so that it is concordant at all levels of the class
        self.modules_json = new_modules_json
        self._modules_json_object.modules_json = new_modules_json
        with open(self.modules_json_path, "w") as modules_json_file:
            json.dump(new_modules_json, modules_json_file)

    def test_modules_json_pass(self):
        self.lint_obj._load()
        results = self.lint_obj.modules_json()
        assert len(results.get("warned", [])) == 0
        assert len(results.get("failed", [])) == 0
        assert len(results.get("passed", [])) > 0

    def test_modules_json_with_repo_not_starting_with_http_fail(self):
        # Change the link of the first repo in modules_json to not start with "http"
        new_modules_json = self.modules_json
        first_repo = next(iter(new_modules_json["repos"]))
        new_modules_json["repos"]["incorrect_repo_link"] = new_modules_json["repos"].pop(first_repo)

        self._update_modules_json(new_modules_json)

        # Check linting results
        results = self.lint_obj.modules_json()
        assert len(results.get("warned", [])) == 0
        assert len(results.get("failed", [])) == 1
        assert len(results.get("passed", [])) == 1  # The repository still contains only installed modules

    def test_modules_json_with_only_subworkflow_entries(self):
        # Keep only "subworkflows" in the first repo in modules_json
        new_modules_json = self.modules_json
        first_repo = next(iter(new_modules_json["repos"]))
        new_modules_json["repos"][first_repo] = {"subworkflows": new_modules_json["repos"][first_repo]["subworkflows"]}

        self._update_modules_json(new_modules_json)

        # Check linting results
        results = self.lint_obj.modules_json()
        assert len(results.get("warned", [])) == 0
        assert len(results.get("failed", [])) == 0
        assert len(results.get("passed", [])) == 0  # There is no subworkflow linting so no "passed" is returned

    def test_modules_json_with_repo_with_no_modules_or_subworkflows_fail(self):
        # Change the first repo in modules_json to have no modules or subworkflows
        new_modules_json = self.modules_json
        first_repo = next(iter(new_modules_json["repos"]))
        new_modules_json["repos"][first_repo] = {}

        self._update_modules_json(new_modules_json)

        # Check linting results
        results = self.lint_obj.modules_json()
        assert len(results.get("warned", [])) == 0
        assert len(results.get("failed", [])) == 1
        assert len(results.get("passed", [])) == 0
