#!/usr/bin/env python
"""
Common utility functions for the nf-core python package.
"""

import datetime
import errno
import json
import logging
import os
import subprocess
import sys

def fetch_wf_config(wf_path, wf=None):
    """Uses Nextflow to retrieve the the configuration variables
    from a Nextflow workflow.

    Args:
        wf_path (str): Nextflow workflow file system path.

    Returns:
        dict: Workflow configuration settings.
    """

    config = dict()
    cache_fn = None
    cache_basedir = None
    cache_path = None

    # Build a cache directory if we can
    if os.path.isdir(os.path.join(os.getenv("HOME"), '.nextflow')):
        cache_basedir = os.path.join(os.getenv("HOME"), '.nextflow', 'nf-core')
        if not os.path.isdir(cache_basedir):
            os.mkdir(cache_basedir)

    # If we're given a workflow object with a commit, see if we have a cached copy
    if cache_basedir and wf and wf.full_name and wf.commit_sha:
        cache_fn = '{}-{}.json'.format(wf.full_name.replace(os.path.sep, '-'), wf.commit_sha)
        cache_path = os.path.join(cache_basedir, cache_fn)
        if os.path.isfile(cache_path):
            logging.debug("Found a config cache, loading: {}".format(cache_path))
            with open(cache_path, 'r') as fh:
                config = json.load(fh)
            return config


    # Call `nextflow config` and pipe stderr to /dev/null
    try:
        with open(os.devnull, 'w') as devnull:
            nfconfig_raw = subprocess.check_output(['nextflow', 'config', '-flat', wf_path], stderr=devnull)
    except OSError as e:
        if e.errno == errno.ENOENT:
            raise AssertionError("It looks like Nextflow is not installed. It is required for most nf-core functions.")
    except subprocess.CalledProcessError as e:
        raise AssertionError("`nextflow config` returned non-zero error code: %s,\n   %s", e.returncode, e.output)
    else:
        for l in nfconfig_raw.splitlines():
            ul = l.decode('utf-8')
            k, v = ul.split(' = ', 1)
            config[k] = v

    # If we can, save a cached copy
    if cache_path:
        logging.debug("Saving config cache: {}".format(cache_path))
        with open(cache_path, 'w') as fh:
            json.dump(config, fh, indent=4)

    return config


def setup_requests_cachedir():
    """Sets up local caching for faster remote HTTP requests.

    Caching directory will be set up in the user's home directory under
    a .nfcore_cache subdir.
    """
    # Only import it if we need it
    import requests_cache

    pyversion = '.'.join(str(v) for v in sys.version_info[0:3])
    cachedir = os.path.join(os.getenv("HOME"), os.path.join('.nfcore', 'cache_'+pyversion))
    if not os.path.exists(cachedir):
        os.makedirs(cachedir)
    requests_cache.install_cache(
        os.path.join(cachedir, 'github_info'),
        expire_after=datetime.timedelta(hours=1),
        backend='sqlite',
    )
