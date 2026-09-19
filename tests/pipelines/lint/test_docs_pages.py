from pathlib import Path

import nf_core.pipelines.lint

from ..test_lint import TestLint


class TestLintDocsPages(TestLint):
    def _lint(self, new_pipeline):
        lint_obj = nf_core.pipelines.lint.PipelineLint(new_pipeline)
        lint_obj._load()
        return lint_obj.docs_pages()

    def _add_page(self, new_pipeline, rel_path):
        page = Path(new_pipeline, rel_path)
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("# A page\n")

    def test_template_pages_pass(self):
        """The template's own usage.md and output.md are rendered, README/CONTRIBUTING are not pages"""
        results = self._lint(self._make_pipeline_copy())

        assert len(results["warned"]) == 0
        assert sorted(r.split("`")[1] for r in results["passed"]) == ["docs/output.md", "docs/usage.md"]

    def test_section_subpages_pass(self):
        """Pages under docs/usage/ and docs/output/ are rendered as sub-pages"""
        new_pipeline = self._make_pipeline_copy()
        self._add_page(new_pipeline, "docs/usage/troubleshooting.md")
        self._add_page(new_pipeline, "docs/output/screening.md")

        results = self._lint(new_pipeline)

        assert len(results["warned"]) == 0
        assert "docs/usage/troubleshooting.md" in " ".join(results["passed"])
        assert "docs/output/screening.md" in " ".join(results["passed"])

    def test_top_level_page_warns(self):
        """A page directly in docs/ is not rendered on the website"""
        new_pipeline = self._make_pipeline_copy()
        self._add_page(new_pipeline, "docs/large_datasets.md")

        results = self._lint(new_pipeline)

        assert len(results["warned"]) == 1
        assert "docs/large_datasets.md" in results["warned"][0]
        assert "docs/usage/large_datasets.md" in results["warned"][0]

    def test_substring_name_still_warns(self):
        """A top-level page merely containing 'usage' in its name is not a section page

        The website's own filter matches the substring anywhere in the path, so this file
        is in fact published today. That is the accidental behaviour this test pins against:
        the check must key on the real rule (exact name, or section directory), not on a
        signal that merely correlates with it.
        """
        new_pipeline = self._make_pipeline_copy()
        self._add_page(new_pipeline, "docs/my_usage_notes.md")

        results = self._lint(new_pipeline)

        assert len(results["warned"]) == 1
        assert "docs/my_usage_notes.md" in results["warned"][0]

    def test_other_subdirectory_warns(self):
        """A page under a directory that is not a section directory is not rendered"""
        new_pipeline = self._make_pipeline_copy()
        self._add_page(new_pipeline, "docs/development/code_conventions.md")

        results = self._lint(new_pipeline)

        assert len(results["warned"]) == 1
        assert "docs/development/code_conventions.md" in results["warned"][0]

    def test_repo_docs_not_checked(self):
        """README, CONTRIBUTING and docs/images/ describe the repo, not the pipeline"""
        new_pipeline = self._make_pipeline_copy()
        self._add_page(new_pipeline, "docs/images/metro_map.md")

        results = self._lint(new_pipeline)

        assert len(results["warned"]) == 0
        assert "README.md" not in " ".join(results["passed"] + results["warned"])
        assert "CONTRIBUTING.md" not in " ".join(results["passed"] + results["warned"])
        assert "metro_map.md" not in " ".join(results["passed"] + results["warned"])

    def test_mdx_pages_treated_as_markdown(self):
        """The website strips both .md and .mdx, so both are pages"""
        new_pipeline = self._make_pipeline_copy()
        self._add_page(new_pipeline, "docs/usage/tutorial.mdx")
        self._add_page(new_pipeline, "docs/benchmark.mdx")

        results = self._lint(new_pipeline)

        assert "docs/usage/tutorial.mdx" in " ".join(results["passed"])
        assert len(results["warned"]) == 1
        assert "docs/benchmark.mdx" in results["warned"][0]

    def test_non_markdown_file_not_a_page(self):
        """A file whose name merely starts with .md is not markdown

        Pins the suffix filter from the other side: the glob is deliberately wide, so
        without the check on the suffix itself a backup or editor file would be reported
        as a documentation page.
        """
        new_pipeline = self._make_pipeline_copy()
        self._add_page(new_pipeline, "docs/usage.md.bak")

        results = self._lint(new_pipeline)

        assert "usage.md.bak" not in " ".join(results["passed"] + results["warned"])

    def test_no_docs_directory(self):
        """A pipeline with no docs/ at all reports nothing rather than failing

        Whether the required pages exist is files_exist's job, not this test's.
        """
        new_pipeline = self._make_pipeline_copy()
        for page in Path(new_pipeline, "docs").glob("*.md"):
            page.unlink()
        Path(new_pipeline, "docs", "images").mkdir(exist_ok=True)
        for image in Path(new_pipeline, "docs", "images").iterdir():
            image.unlink()
        Path(new_pipeline, "docs", "images").rmdir()
        Path(new_pipeline, "docs").rmdir()

        results = self._lint(new_pipeline)

        assert results == {"passed": [], "warned": [], "ignored": []}

    def test_ignored_in_config(self):
        """A working document kept in docs/ on purpose can be listed in .nf-core.yml"""
        new_pipeline = self._make_pipeline_copy()
        self._add_page(new_pipeline, "docs/implementation_design.md")

        lint_obj = nf_core.pipelines.lint.PipelineLint(new_pipeline)
        lint_obj._load()
        lint_obj.lint_config = {"docs_pages": ["docs/implementation_design.md"]}
        results = lint_obj.docs_pages()

        assert len(results["warned"]) == 0
        assert len(results["ignored"]) == 1
        assert "docs/implementation_design.md" in results["ignored"][0]
