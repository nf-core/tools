#!/usr/bin/env python
""" Code to handle DSL2 module imports from nf-core/modules
"""

from __future__ import print_function

import os
import requests
import sys
import tempfile

def get_modules_filetree():
    """
    Fetch the file list from nf-core/modules
    """
    r = requests.get("https://api.github.com/repos/nf-core/modules/git/trees/master?recursive=1")
    if r.status_code == 200:
        print('Success!')
    elif r.status_code == 404:
        print('Not Found.')
