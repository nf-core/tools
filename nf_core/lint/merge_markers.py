#!/usr/bin/env python

import logging
import os
import io
import fnmatch

import nf_core.utils

log = logging.getLogger(__name__)


def merge_markers(self):
    """Check for remaining merge markers.

    This test looks for remaining merge markers in the code, e.g.:
    >>>>>>> or <<<<<<<

    """
    passed = []
    failed = []
    ignored = []

    ignored_config = self.lint_config.get("merge_markers", [])

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
            # File ignored in config
            if os.path.relpath(os.path.join(root, fname), self.wf_path) in ignored_config:
                ignored.append(f"Ignoring file `{os.path.join(root, fname)}`")
                continue
            # Skip binary files
            if nf_core.utils.is_file_binary(os.path.join(root, fname)):
                continue
            try:
                with io.open(os.path.join(root, fname), "rt", encoding="latin1") as fh:
                    for l in fh:
                        if ">>>>>>>" in l:
                            failed.append(f"Merge marker '>>>>>>>' in `{os.path.join(root, fname)}`: {l[:30]}")
                        if "<<<<<<<" in l:
                            failed.append(f"Merge marker '<<<<<<<' in `{os.path.join(root, fname)}`: {l[:30]}")
            except FileNotFoundError:
                log.debug(f"Could not open file {os.path.join(root, fname)} in merge_markers lint test")
    if len(failed) == 0:
        passed.append("No merge markers found in pipeline files")
    return {"passed": passed, "failed": failed, "ignored": ignored}
