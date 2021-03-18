#!/usr/bin/env python

import logging
import os
import io
import fnmatch

log = logging.getLogger(__name__)


def merge_markers(self):
    """Check for remaining merge markers.

    This test looks for remaining merge markers in the code, e.g.:
    >>>>>>> or <<<<<<<


    """
    passed = []
    failed = []

    ignore = [".git"]
    if os.path.isfile(os.path.join(self.wf_path, ".gitignore")):
        with io.open(os.path.join(self.wf_path, ".gitignore"), "rt", encoding="latin1") as fh:
            for l in fh:
                ignore.append(os.path.basename(l.strip().rstrip("/")))
    for root, dirs, files in os.walk(self.wf_path, topdown=True):
        # Ignore files
        for i_base in ignore:
            i = os.path.join(root, i_base)
            dirs[:] = [d for d in dirs if not fnmatch.fnmatch(os.path.join(root, d), i)]
            files[:] = [f for f in files if not fnmatch.fnmatch(os.path.join(root, f), i)]
        for fname in files:
            try:
                with io.open(os.path.join(root, fname), "rt", encoding="latin1") as fh:
                    for l in fh:
                        if ">>>>>>>" in l:
                            failed.append(f"Merge marker '>>>>>>>' in `{os.path.join(root, fname)}`: {l}")
                        if "<<<<<<<" in l:
                            failed.append(f"Merge marker '<<<<<<<' in `{os.path.join(root, fname)}`: {l}")
                            print(root)
            except FileNotFoundError:
                log.debug(f"Could not open file {os.path.join(root, fname)} in merge_markers lint test")
    if len(failed) == 0:
        passed.append("No merge markers found in pipeline files")
    return {"passed": passed, "failed": failed}
