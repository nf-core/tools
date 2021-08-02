#!/usr/bin/env python

import fnmatch
import os
import nf_core.lint

docs_basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_src", "pipeline_lint_tests")

# Get list of existing .md files
existing_docs = []
for fn in os.listdir(docs_basedir):
    if fnmatch.fnmatch(fn, "*.md") and not fnmatch.fnmatch(fn, "index.md"):
        existing_docs.append(os.path.join(docs_basedir, fn))

# Make .md file for each test name
lint_obj = nf_core.lint.PipelineLint("", True)
md_template = """# {0}

```{eval-rst}
.. automethod:: nf_core.lint.PipelineLint.{0}
```

"""

for test_name in lint_obj.lint_tests:
    fn = os.path.join(docs_basedir, "{}.md".format(test_name))
    if os.path.exists(fn):
        existing_docs.remove(fn)
    else:
        with open(fn, "w") as fh:
            fh.write(md_template.format(test_name))

for fn in existing_docs:
    os.remove(fn)
