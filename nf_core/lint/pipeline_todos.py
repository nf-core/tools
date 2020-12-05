#!/usr/bin/env python

import os
import io
import fnmatch


def pipeline_todos(self):
    """ Go through all template files looking for the string 'TODO nf-core:' """
    passed = []
    warned = []
    failed = []

    ignore = [".git"]
    if os.path.isfile(os.path.join(self.path, ".gitignore")):
        with io.open(os.path.join(self.path, ".gitignore"), "rt", encoding="latin1") as fh:
            for l in fh:
                ignore.append(os.path.basename(l.strip().rstrip("/")))
    for root, dirs, files in os.walk(self.path):
        # Ignore files
        for i in ignore:
            dirs = [d for d in dirs if not fnmatch.fnmatch(os.path.join(root, d), i)]
            files = [f for f in files if not fnmatch.fnmatch(os.path.join(root, f), i)]
        for fname in files:
            with io.open(os.path.join(root, fname), "rt", encoding="latin1") as fh:
                for l in fh:
                    if "TODO nf-core" in l:
                        l = (
                            l.replace("<!--", "")
                            .replace("-->", "")
                            .replace("# TODO nf-core: ", "")
                            .replace("// TODO nf-core: ", "")
                            .replace("TODO nf-core: ", "")
                            .strip()
                        )
                        warned.append("TODO string in `{}`: _{}_".format(fname, l))

    return {"passed": passed, "warned": warned, "failed": failed}
