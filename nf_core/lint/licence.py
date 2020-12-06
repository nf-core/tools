#!/usr/bin/env python

import os


def licence(self):
    """Checks licence file is MIT.

    Currently the checkpoints are:
        * licence file must be long enough (4 or more lines)
        * licence contains the string *without restriction*
        * licence doesn't have any placeholder variables
    """
    passed = []
    warned = []
    failed = []

    for l in ["LICENSE", "LICENSE.md", "LICENCE", "LICENCE.md"]:
        fn = os.path.join(self.wf_path, l)
        if os.path.isfile(fn):
            content = ""
            with open(fn, "r") as fh:
                content = fh.read()

            # needs at least copyright, permission, notice and "as-is" lines
            nl = content.count("\n")
            if nl < 4:
                failed.append("Number of lines too small for a valid MIT license file: {}".format(fn))

            # determine whether this is indeed an MIT
            # license. Most variations actually don't contain the
            # string MIT Searching for 'without restriction'
            # instead (a crutch).
            if not "without restriction" in content:
                failed.append("Licence file did not look like MIT: {}".format(fn))

            # check for placeholders present in
            # - https://choosealicense.com/licenses/mit/
            # - https://opensource.org/licenses/MIT
            # - https://en.wikipedia.org/wiki/MIT_License
            placeholders = {"[year]", "[fullname]", "<YEAR>", "<COPYRIGHT HOLDER>", "<year>", "<copyright holders>"}
            if any([ph in content for ph in placeholders]):
                failed.append("Licence file contains placeholders: {}".format(fn))

            passed.append("Licence check passed")

    return {"passed": passed, "warned": warned, "failed": failed}
