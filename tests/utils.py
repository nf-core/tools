#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper functions for tests
"""

import functools
import tempfile
from pathlib import Path

OLD_TRIMGALORE_SHA = "20d8250d9f39ddb05dfb437603aaf99b5c0b2b41"


def with_temporary_folder(func):
    """
    Call the decorated funtion under the tempfile.TemporaryDirectory
    context manager. Pass the temporary directory name to the decorated
    function
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with tempfile.TemporaryDirectory() as tmpdirname:
            return func(*args, Path(tmpdirname), **kwargs)

    return wrapper


def with_temporary_file(func):
    """
    Call the decorated funtion under the tempfile.NamedTemporaryFile
    context manager. Pass the opened file handle to the decorated function
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with tempfile.NamedTemporaryFile() as tmpfile:
            return func(*args, Path(tmpfile.name), **kwargs)

    return wrapper
