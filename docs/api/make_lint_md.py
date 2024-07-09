#!/usr/bin/env python
from pathlib import Path

import nf_core.modules.lint
import nf_core.pipelines.lint
import nf_core.subworkflows.lint


def create_docs(docs_basedir, lint_tests, md_template):
    docs_basedir.mkdir(parents=True, exist_ok=True)
    existing_docs = list(docs_basedir.glob("*.md"))
    existing_docs.remove(docs_basedir / "index.md")

    for test_name in lint_tests:
        fn = docs_basedir / f"{test_name}.md"
        if fn.exists():
            existing_docs.remove(fn)
        else:
            with open(fn, "w") as fh:
                fh.write(md_template.format(test_name))

    for fn in existing_docs:
        fn.unlink()


def create_index_file(basedir, title):
    index_file = basedir / "index.md"
    with open(index_file, "w") as fh:
        fh.write(f"# {title}\n\n")
        for fn in sorted(basedir.glob("*.md")):
            if fn.name != "index.md":
                fh.write(f"    - [{fn.stem}](./{fn.stem}/)\n")


# Create the pipeline docs
pipeline_lint_docs_basedir = Path(__file__).resolve().parent / "_src" / "pipeline_lint_tests"
create_docs(
    pipeline_lint_docs_basedir,
    nf_core.pipelines.lint.PipelineLint._get_all_lint_tests(True),
    """# {0}

    ```{{eval-rst}}
    .. automethod:: nf_core.pipelines.lint.PipelineLint.{0}
    ```
    """,
)
create_index_file(pipeline_lint_docs_basedir, "Pipeline Lint Tests")

# Create the modules docs
modules_lint_docs_basedir = Path(__file__).resolve().parent / "_src" / "module_lint_tests"
create_docs(
    modules_lint_docs_basedir,
    set(nf_core.modules.lint.ModuleLint.get_all_module_lint_tests(is_pipeline=True)).union(
        nf_core.modules.lint.ModuleLint.get_all_module_lint_tests(is_pipeline=False)
    ),
    """# {0}

```{{eval-rst}}
.. automethod:: nf_core.modules.lint.ModuleLint.{0}
```
""",
)
create_index_file(modules_lint_docs_basedir, "Module Lint Tests")

# Create the subworkflow docs
subworkflow_lint_docs_basedir = Path(__file__).resolve().parent / "_src" / "subworkflow_lint_tests"
create_docs(
    subworkflow_lint_docs_basedir,
    set(nf_core.subworkflows.lint.SubworkflowLint.get_all_subworkflow_lint_tests(is_pipeline=True)).union(
        nf_core.subworkflows.lint.SubworkflowLint.get_all_subworkflow_lint_tests(is_pipeline=False)
    ),
    """# {0}

```{{eval-rst}}
.. automethod:: nf_core.subworkflows.lint.SubworkflowLint.{0}
```
""",
)
create_index_file(subworkflow_lint_docs_basedir, "Subworkflow Lint Tests")
