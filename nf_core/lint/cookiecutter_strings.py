#!/usr/bin/env python

import io
import os
import re


def cookiecutter_strings(self):
    """Check for 'cookiecutter' placeholders.

    The ``nf-core create`` pipeline template uses
    `cookiecutter <https://github.com/cookiecutter/cookiecutter>`_ behind the scenes.

    This lint test fails if any cookiecutter template variables such as
    ``{{ cookiecutter.pipeline_name }}`` are found in your pipeline code.

    Finding a placeholder like this means that something was probably copied and pasted
    from the template without being properly rendered for your pipeline.
    """
    passed = []
    failed = []

    # Loop through files, searching for string
    num_matches = 0
    for fn in self.files:
        with io.open(fn, "r", encoding="latin1") as fh:
            lnum = 0
            for l in fh:
                lnum += 1
                cc_matches = re.findall(r"{{\s*cookiecutter[^}]*}}", l)
                if len(cc_matches) > 0:
                    for cc_match in cc_matches:
                        failed.append("Found a cookiecutter template string in `{}` L{}: {}".format(fn, lnum, cc_match))
                        num_matches += 1
    if num_matches == 0:
        passed.append("Did not find any cookiecutter template strings ({} files)".format(len(self.files)))

    return {"passed": passed, "failed": failed}
