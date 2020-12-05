#!/usr/bin/env python

import io
import os
import re
import subprocess


def cookiecutter_strings(self):
    """
    Look for the string 'cookiecutter' in all pipeline files.
    Finding it probably means that there has been a copy+paste error from the template.
    """
    passed = []
    warned = []
    failed = []

    try:
        # First, try to get the list of files using git
        git_ls_files = subprocess.check_output(["git", "ls-files"], cwd=self.path).splitlines()
        list_of_files = [os.path.join(self.path, s.decode("utf-8")) for s in git_ls_files]
    except subprocess.CalledProcessError as e:
        # Failed, so probably not initialised as a git repository - just a list of all files
        log.debug("Couldn't call 'git ls-files': {}".format(e))
        list_of_files = []
        for subdir, dirs, files in os.walk(self.path):
            for file in files:
                list_of_files.append(os.path.join(subdir, file))

    # Loop through files, searching for string
    num_matches = 0
    num_files = 0
    for fn in list_of_files:
        num_files += 1
        try:
            with io.open(fn, "r", encoding="latin1") as fh:
                lnum = 0
                for l in fh:
                    lnum += 1
                    cc_matches = re.findall(r"{{\s*cookiecutter[^}]*}}", l)
                    if len(cc_matches) > 0:
                        for cc_match in cc_matches:
                            failed.append(
                                "Found a cookiecutter template string in `{}` L{}: {}".format(fn, lnum, cc_match)
                            )
                            num_matches += 1
        except FileNotFoundError as e:
            log.warn("`git ls-files` returned '{}' but could not open it!".format(fn))
    if num_matches == 0:
        passed.append("Did not find any cookiecutter template strings ({} files)".format(num_files))

    return {"passed": passed, "warned": warned, "failed": failed}
