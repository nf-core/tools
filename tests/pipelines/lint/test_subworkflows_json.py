from ..test_lint import TestLint


class TestLintSubworkflowsJson(TestLint):
    def test_subworkflows_json_pass(self):
        self.lint_obj._load()
        results = self.lint_obj.subworkflows_json()
        assert len(results.get("warned", [])) == 0
        assert len(results.get("failed", [])) == 0
        assert len(results.get("passed", [])) > 0
