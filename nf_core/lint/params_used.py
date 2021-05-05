#!/usr/bin/env python

import os


def params_used(self):
    """Check for that params in ``nextflow.config`` are mentioned in ``main.nf``."""

    ignore_params_template = [
        "params.custom_config_version",
        "params.custom_config_base",
        "params.config_profile_name",
        "params.show_hidden_params",
        "params.schema_ignore_params",
    ]
    ignore_params = self.lint_config.get("params_used", [])

    passed = []
    warned = []
    ignored = []

    with open(os.path.join(self.wf_path, "main.nf"), "r") as fh:
        main_nf = fh.read()

    for cf in self.nf_config.keys():
        if not cf.startswith("params.") or cf in ignore_params_template:
            continue
        if cf in ignore_params:
            ignored.append("Config variable ignored: {}".format(self._wrap_quotes(cf)))
            continue
        if cf in main_nf:
            passed.append("Config variable found in `main.nf`: {}".format(self._wrap_quotes(cf)))
        else:
            warned.append("Config variable not found in `main.nf`: {}".format(self._wrap_quotes(cf)))

    return {"passed": passed, "warned": warned, "ignored": ignored}
