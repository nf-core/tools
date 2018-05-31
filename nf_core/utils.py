#!/usr/bin/env python
"""
Common utility functions for the nf-core python package.
"""

import logging
import os
import subprocess

def fetch_wf_config(wf_path):
    """
    Use nextflow to retrieve the nf configuration variables from a workflow
    """

    config = dict()
    # Call `nextflow config` and pipe stderr to /dev/null
    try:
        with open(os.devnull, 'w') as devnull:
            nfconfig_raw = subprocess.check_output(['nextflow', 'config', '-flat', wf_path], stderr=devnull)
    except subprocess.CalledProcessError as e:
        raise AssertionError("`nextflow config` returned non-zero error code: %s,\n   %s", e.returncode, e.output)
    else:
        for l in nfconfig_raw.splitlines():
            ul = l.decode()
            k, v = ul.split(' = ', 1)
            config[k] = v
    return config
