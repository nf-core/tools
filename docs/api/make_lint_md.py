#!/usr/bin/env python

import fnmatch
import os
import nf_core.lint
import nf_core.modules.lint


def make_docs(docs_basedir, lint_tests, md_template):
    # Get list of existing .md files
    existing_docs = []
    for fn in os.listdir(docs_basedir):
        if fnmatch.fnmatch(fn, "*.md") and not fnmatch.fnmatch(fn, "index.md"):
            existing_docs.append(os.path.join(docs_basedir, fn))

    for test_name in lint_tests:
        fn = os.path.join(docs_basedir, "{}.md".format(test_name))
        if os.path.exists(fn):
            existing_docs.remove(fn)
        else:
            with open(fn, "w") as fh:
                fh.write(md_template.format(test_name))

    for fn in existing_docs:
        os.remove(fn)


# Create the pipeline docs
pipeline_docs_basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_src", "pipeline_lint_tests")
make_docs(
    pipeline_docs_basedir,
    nf_core.lint.PipelineLint._get_all_lint_tests(),
    """# {0}

    ```{eval-rst}
    .. automethod:: nf_core.lint.PipelineLint.{0}
    ```

    """,
)

# Create the modules lint docs
modules_docs_basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_src", "modules_lint_tests")
make_docs(
    modules_docs_basedir,
    nf_core.modules.lint.ModuleLint._get_all_lint_tests(),
    """# {0}

    ```{eval-rst}
    .. automethod:: nf_core.modules.lint.ModuleLint.{0}
    ```

    """,
)
