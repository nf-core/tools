#!/usr/bin/env python
""" Main nf_core module file.

Shouldn't do much, as everything is under subcommands.
"""

import pkg_resources

try:
    __version__ = pkg_resources.get_distribution("nf_core").version
except:
    # Needed for loading from unittest
    __version__ = "unknown version"
