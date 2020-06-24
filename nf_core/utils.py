#!/usr/bin/env python
"""
Common utility functions for the nf-core python package.
"""

import datetime
import errno
import json
import hashlib
import logging
import os
import re
import subprocess
import sys

def fetch_wf_config(wf_path):
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
    cache_fn = None
    # Make a filename based on file contents
    concat_hash = ''
    for fn in ['nextflow.config', 'main.nf']:
        try:
            with open(os.path.join(wf_path, fn), 'rb') as fh:
                concat_hash += hashlib.sha256(fh.read()).hexdigest()
        except FileNotFoundError as e:
            pass
    # Hash the hash
    if len(concat_hash) > 0:
        bighash = hashlib.sha256(concat_hash.encode('utf-8')).hexdigest()
        cache_fn = 'wf-config-cache-{}.json'.format(bighash[:25])

    if cache_basedir and cache_fn:
        cache_path = os.path.join(cache_basedir, cache_fn)
        if os.path.isfile(cache_path):
            logging.debug("Found a config cache, loading: {}".format(cache_path))
            with open(cache_path, 'r') as fh:
                config = json.load(fh)
            return config
    logging.debug("No config cache found")


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
            try:
                k, v = ul.split(' = ', 1)
                config[k] = v
            except ValueError:
                logging.debug("Couldn't find key=value config pair:\n  {}".format(ul))

    # Scrape main.nf for additional parameter declarations
    # Values in this file are likely to be complex, so don't both trying to capture them. Just get the param name.
    try:
        main_nf = os.path.join(wf_path, 'main.nf')
        with open(main_nf, 'r') as fh:
            for l in fh:
                match = re.match(r'^\s*(params\.[a-zA-Z0-9_]+)\s*=', l)
                if match:
                    config[match.group(1)] = 'false'
    except FileNotFoundError as e:
        logging.debug("Could not open {} to look for parameter declarations - {}".format(main_nf, e))

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
