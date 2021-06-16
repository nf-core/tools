#!/usr/bin/env python
"""
The ModuleCreate class handles generating of module templates
"""


class ModuleUpdate(object):
    def __init__(
        self, directory=".", tool="", author=None, process_label=None, has_meta=None, force=False, conda_name=None
    ):
        super().__init__()
