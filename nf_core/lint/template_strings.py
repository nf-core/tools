#!/usr/bin/env python

import io
import mimetypes
import re


def template_strings(self):
    """Check for template placeholders.

    The ``nf-core create`` pipeline template uses
    `Jinja <https://jinja.palletsprojects.com/en/2.11.x/>`_ behind the scenes.

    This lint test fails if any Jinja template variables such as
    ``{{ pipeline_name }}`` are found in your pipeline code.

    Finding a placeholder like this means that something was probably copied and pasted
    from the template without being properly rendered for your pipeline.

    This test ignores any double-brackets prefixed with a dollar sign, such as
    ``${{ secrets.AWS_ACCESS_KEY_ID }}`` as these placeholders are used in GitHub Actions workflows.
    """
    passed = []
    failed = []

    # Loop through files, searching for string
    num_matches = 0
    for fn in self.files:

        # Skip binary files
        binary_ftypes = ["image", "application/java-archive"]
        (ftype, encoding) = mimetypes.guess_type(fn)
        if encoding is not None or (ftype is not None and any([ftype.startswith(ft) for ft in binary_ftypes])):
            continue

        with io.open(fn, "r", encoding="latin1") as fh:
            lnum = 0
            for l in fh:
                lnum += 1
                cc_matches = re.findall(r"[^$]{{[^:}]*}}", l)
                if len(cc_matches) > 0:
                    for cc_match in cc_matches:
                        failed.append("Found a Jinja template string in `{}` L{}: {}".format(fn, lnum, cc_match))
                        num_matches += 1
    if num_matches == 0:
        passed.append("Did not find any Jinja template strings ({} files)".format(len(self.files)))

    return {"passed": passed, "failed": failed}
