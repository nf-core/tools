#!/usr/bin/env python

import os


def docker(self):
    """Checks that Dockerfile contains the string ``FROM``."""
    passed = []
    warned = []
    failed = []

    if os.path.join(self.path, "Dockerfile") in self.files:
        with open(os.path.join(self.path, "Dockerfile"), "r") as fh:
            dockerfile_contents = fh.read()

        # Implicitly also checks if empty.
        if "FROM " in dockerfile_contents:
            passed.append("Dockerfile check passed")
        else:
            failed.append("Dockerfile check failed")

    return {"passed": passed, "warned": warned, "failed": failed}
