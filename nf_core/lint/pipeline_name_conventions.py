#!/usr/bin/env python


def pipeline_name_conventions(self):
    """Check whether pipeline name adheres to lower case/no hyphen naming convention"""
    passed = []
    warned = []
    failed = []

    if self.pipeline_name.islower() and self.pipeline_name.isalnum():
        passed.append("Name adheres to nf-core convention")
    if not self.pipeline_name.islower():
        warned.append("Naming does not adhere to nf-core conventions: Contains uppercase letters")
    if not self.pipeline_name.isalnum():
        warned.append("Naming does not adhere to nf-core conventions: Contains non alphanumeric characters")

    return {"passed": passed, "warned": warned, "failed": failed}
