import shutil
from pathlib import Path

import pytest
import yaml

import nf_core.modules.lint
from nf_core.modules.lint.main_nf import check_ext_directive, check_script_section, check_typed_sections
from nf_core.utils import check_nextflow_version

from ...test_modules import TestModules
from .test_lint_utils import MockModuleLint

TYPED_MODULE = Path(__file__).parents[2] / "data" / "typed_module" / "preseq_lcextrap"
STATIC_TYPES_MIN_NF_VERSION = (26, 4, 0, False)

TYPED_SECTIONS = """
    input:
    record(
        id: String,
        meta: Record?,
        bam: Path
    )

    output:
    record(
        id: id,
        meta: meta,
        txt: file("*.txt")
    )

    topic:
    record(process: "${task.process}", tool: 'foo', version: eval("foo --version")) >> 'versions'

    script:
"""


def _process(body: str) -> str:
    return "process FOO {\n" + body + '    """\n    foo\n    """\n}\n'


def _results(mock_lint):
    passed = {result[1] for result in mock_lint.passed}
    failed = {result[1] for result in mock_lint.failed}
    return passed, failed


def test_typed_sections_pass():
    mock_lint = MockModuleLint()
    inputs, emits, topics = check_typed_sections(mock_lint, _process(TYPED_SECTIONS))
    passed, failed = _results(mock_lint)

    assert inputs == ["id", "meta", "bam"]
    assert emits == ["id", "meta", "txt"]
    assert topics == ["versions"]
    assert failed == set()
    assert passed == {"main_nf_record_input", "main_nf_record_output", "wrong_version_output"}


@pytest.mark.parametrize(
    "old,new,lint_test",
    [
        ("        bam: Path\n    )", "        bam: Path\n    )\n    record(bai: Path)", "main_nf_record_input"),
        ("        id: String,", "", "main_nf_record_input"),
        ("        meta: meta,", "", "main_nf_record_output"),
        ('process: "${task.process}"', "process: 'FOO'", "wrong_version_output"),
        ("tool: 'foo', ", "", "wrong_version_output"),
    ],
)
def test_typed_sections_fail(old, new, lint_test):
    mock_lint = MockModuleLint()
    check_typed_sections(mock_lint, _process(TYPED_SECTIONS.replace(old, new)))
    _, failed = _results(mock_lint)
    assert failed == {lint_test}


def test_typed_sections_without_record_input():
    mock_lint = MockModuleLint()
    inputs, _, _ = check_typed_sections(
        mock_lint, _process(TYPED_SECTIONS.replace("record(\n        id: String,", "("))
    )
    _, failed = _results(mock_lint)
    assert inputs == []
    assert "main_nf_record_input" in failed


@pytest.mark.parametrize(
    "ext_lines,failed_test",
    [
        (
            [
                "    ext [\n",
                "        prefix: { output_prefix ?: id },\n",
                "        args: { foo_args ?: '' }\n",
                "    ]\n",
            ],
            None,
        ),
        (["    ext [prefix: { output_prefix ?: id }, args: { foo_args ?: '' }]\n"], None),
        (["    ext [\n", "        prefix: { output_prefix ?: id }\n", "    ]\n"], "main_nf_ext_directive"),
        ([], "main_nf_ext_directive"),
    ],
)
def test_ext_directive(ext_lines, failed_test):
    mock_lint = MockModuleLint()
    check_ext_directive(
        mock_lint,
        _process("".join(ext_lines) + "    script:\n"),
        ['    "foo ${task.ext.args} -o ${task.ext.prefix}.txt"\n'],
    )
    passed, failed = _results(mock_lint)
    if failed_test:
        assert failed == {failed_test}
    else:
        assert passed == {"main_nf_ext_directive"}


def test_typed_script_section_does_not_require_def_prefix():
    script = ['    "foo ${task.ext.args} -o ${task.ext.prefix}.txt"\n']
    mock_lint = MockModuleLint()
    mock_lint.has_meta = True
    check_script_section(mock_lint, script, typed=True)
    assert "main_nf_meta_prefix" not in {result[1] for result in mock_lint.failed + mock_lint.passed}

    mock_lint = MockModuleLint()
    mock_lint.has_meta = True
    check_script_section(mock_lint, script)
    assert "main_nf_meta_prefix" in {result[1] for result in mock_lint.failed}


def test_typed_script_section_rejects_meta_keys():
    mock_lint = MockModuleLint()
    check_script_section(mock_lint, ['    "foo --sample ${meta.id} ${task.ext.args}"\n'], typed=True)
    assert [result[1] for result in mock_lint.failed] == ["main_nf_meta_key"]


class TestTypedModuleLint(TestModules):
    """Lint a module that uses static types and records"""

    def setUp(self):
        super().setUp()
        self.module_dir = Path(self.nfcore_modules, "modules", "nf-core", "preseq", "lcextrap")
        shutil.copytree(TYPED_MODULE, self.module_dir)
        self.meta_yml_path = self.module_dir / "meta.yml"
        self.main_nf_path = self.module_dir / "main.nf"

    def _lint(self, fix=False):
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules, fix=fix)
        module_lint.lint(print_results=False, module="preseq/lcextrap")
        return module_lint

    @staticmethod
    def _failed(module_lint) -> dict[str, str]:
        """Failed lint tests, without those that depend on the environment rather than the module.

        `meta_yml_valid` depends on whether the nf-core/modules meta.yml schema accepts records,
        and `nextflow inspect` can only resolve the containers of a typed module with a Nextflow
        version that supports static types.
        """
        ignored = {"meta_yml_valid"}
        if not check_nextflow_version(STATIC_TYPES_MIN_NF_VERSION, silent=True):
            ignored |= {"docker_tag", "singularity_tag"}
        return {result.lint_test: result.message for result in module_lint.failed if result.lint_test not in ignored}

    def _edit_meta_yml(self, edit):
        meta_yml = yaml.safe_load(self.meta_yml_path.read_text())
        edit(meta_yml)
        self.meta_yml_path.write_text(yaml.safe_dump(meta_yml, sort_keys=False))

    def test_lint_typed_module(self):
        module_lint = self._lint()
        passed = {result.lint_test for result in module_lint.passed}
        failed = self._failed(module_lint)

        assert failed == {}, f"Linting failed with {failed}"
        assert {
            "main_nf_record_input",
            "main_nf_record_output",
            "main_nf_no_when",
            "main_nf_ext_directive",
            "main_nf_meta_output",
            "main_nf_version_topic",
            "wrong_version_output",
            "correct_meta_inputs",
            "correct_meta_outputs",
            "correct_meta_topics",
            "test_snap_versions",
        } <= passed

    def test_lint_typed_module_with_when_block(self):
        main_nf = self.main_nf_path.read_text()
        self.main_nf_path.write_text(
            main_nf.replace("    script:\n", "    when:\n    task.ext.when == null || task.ext.when\n\n    script:\n")
        )
        module_lint = self._lint()
        assert set(self._failed(module_lint)) == {"main_nf_no_when"}

    def test_lint_typed_module_meta_yml_mismatch(self):
        def edit(meta_yml):
            meta_yml["input"][0]["fields"]["meta"].pop("optional")
            meta_yml["output"][0]["fields"]["log"]["value"] = 'file("*.txt")'
            meta_yml["topics"]["versions"][0]["fields"]["tool"]["value"] = "'foo'"

        self._edit_meta_yml(edit)
        module_lint = self._lint()
        failed = self._failed(module_lint)

        assert set(failed) == {
            "correct_meta_inputs",
            "correct_meta_outputs",
            "correct_meta_topics",
        }
        assert "`meta` should have optional `True`, found `False`" in failed["correct_meta_inputs"]
        assert '`log` should have value `file("*.log")`' in failed["correct_meta_outputs"]
        assert "Topic `versions`: `tool` should have value `'preseq'`" in failed["correct_meta_topics"]

    def test_lint_typed_module_fix(self):
        original = yaml.safe_load(self.meta_yml_path.read_text())

        def edit(meta_yml):
            fields = meta_yml["input"][0]["fields"]
            fields["meta"].pop("optional")
            fields["stale"] = {"type": "Path", "description": "Not in main.nf"}
            del meta_yml["output"][0]["fields"]["lc_extrap"]
            meta_yml["output"][0]["fields"]["log"]["value"] = 'file("*.txt")'
            del meta_yml["topics"]

        self._edit_meta_yml(edit)
        module_lint = self._lint(fix=True)
        assert self._failed(module_lint) == {}

        fixed = yaml.safe_load(self.meta_yml_path.read_text())
        assert fixed["input"] == original["input"]
        assert fixed["output"][0]["fields"]["log"] == original["output"][0]["fields"]["log"]
        assert fixed["output"][0]["fields"]["lc_extrap"] == {"value": 'file("*.lc_extrap.txt")', "type": "Path"}
        assert fixed["topics"] == original["topics"]

    def test_fix_leaves_matching_typed_meta_yml_unchanged(self):
        original = yaml.safe_load(self.meta_yml_path.read_text())
        self._lint(fix=True)
        assert yaml.safe_load(self.meta_yml_path.read_text()) == original
