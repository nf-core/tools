#!/usr/bin/env python

import fnmatch
import os
import nf_core.lint

basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_src", "lint_tests")

# Delete existing .rst files
for fn in os.listdir(basedir):
    if fnmatch.fnmatch(fn, "*.rst") and not fnmatch.fnmatch(fn, "index.rst"):
        os.remove(os.path.join(basedir, fn))

# Make .rst file for each test name
lint_obj = nf_core.lint.PipelineLint("", True)
rst_template = """{0}
{1}

.. automethod:: nf_core.lint.PipelineLint.{0}
"""

for test_name in lint_obj.lint_tests:
    with open(os.path.join(basedir, "{}.rst".format(test_name)), "w") as fh:
        fh.write(rst_template.format(test_name, len(test_name) * "="))
