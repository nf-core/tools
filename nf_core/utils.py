#!/usr/bin/env python
"""
Common utility functions for the nf-core python package.
"""

import datetime
import os
import subprocess
import tempfile

def fetch_wf_config(wf_path):
    """
    Use nextflow to retrieve the nf configuration variables from a workflow
    """

    config = dict()
    # Call `nextflow config` and pipe stderr to /dev/null
    try:
        with open(os.devnull, 'w') as devnull:
            nfconfig_raw = subprocess.check_output(['nextflow', 'config', '-flat', wf_path], stderr=devnull)
    except OSError as e:
        if e.errno == os.errno.ENOENT:
            raise AssertionError("It looks like Nextflow is not installed. It is required for most nf-core functions.")
    except subprocess.CalledProcessError as e:
        raise AssertionError("`nextflow config` returned non-zero error code: %s,\n   %s", e.returncode, e.output)
    else:
        for l in nfconfig_raw.splitlines():
            ul = l.decode('utf-8')
            k, v = ul.split(' = ', 1)
            config[k] = v
    return config


def setup_requests_cachedir():
    """
    Set up local caching for requests to speed up remote queries
    """

    # Only import it if we need it
    import requests_cache

    cachedir = os.path.join(tempfile.gettempdir(), 'nfcore_cache')
    if not os.path.exists(cachedir):
        os.mkdir(cachedir)
    requests_cache.install_cache(
        os.path.join(cachedir, 'nfcore_cache'),
        expire_after=datetime.timedelta(hours=1),
        backend='sqlite',
    )
    # Make world-writeable so that multi-user installations work
    os.chmod(cachedir, 0o777)
    os.chmod(os.path.join(cachedir, 'nfcore_cache.sqlite'), 0o777)
