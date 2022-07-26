#!/usr/bin/env python

import os
from pathlib import Path

import nf_core.lint
import nf_core.modules.lint


def make_docs(docs_dir, lint_tests, md_template):
    # Get list of existing .md files
    existing_docs = []
    for file in docs_dir.glob("*.md"):
        if file.name != "index.md":
            existing_docs.append(docs_dir / file)

    for test_name in lint_tests:
        file = docs_dir / f"{test_name}.md"
        if file.exists():
            existing_docs.remove(file)
        else:
            with open(file, "w") as fh:
                fh.write(md_template.format(test_name))
                print(test_name)

    for file in existing_docs:
        os.remove(file)


# Create the pipeline docs
docs_basedir = Path(__file__).absolute().parent / "_src"
pipeline_docs_basedir = docs_basedir / "pipeline_lint_tests"
make_docs(
    pipeline_docs_basedir,
    nf_core.lint.PipelineLint._get_all_lint_tests(True),
    """# {0}

```{{eval-rst}}
.. automethod:: nf_core.lint.PipelineLint.{0}
```
""",
)

# Create the modules lint docs
modules_docs_basedir = docs_basedir / "module_lint_tests"
make_docs(
    modules_docs_basedir,
    nf_core.modules.lint.ModuleLint._get_all_lint_tests(),
    """# {0}

```{{eval-rst}}
.. automethod:: nf_core.modules.lint.ModuleLint.{0}
```
""",
)
