#!/usr/bin/env python

import os


def docker(self):
    """Checks that Dockerfile contains the string ``FROM``."""
    passed = []
    warned = []
    failed = []

    if "Dockerfile" in self.files:
        fn = os.path.join(self.path, "Dockerfile")
        content = ""
        with open(fn, "r") as fh:
            content = fh.read()

        # Implicitly also checks if empty.
        if "FROM " in content:
            passed.append("Dockerfile check passed")
            self.dockerfile = [line.strip() for line in content.splitlines()]
        else:
            failed.append("Dockerfile check failed")
    return {"passed": passed, "warned": warned, "failed": failed}
