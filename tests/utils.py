#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper functions for tests
"""

import functools
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

OLD_TRIMGALORE_SHA = "06348dffce2a732fc9e656bdc5c64c3e02d302cb"
OLD_TRIMGALORE_BRANCH = "mimic-old-trimgalore"
GITLAB_URL = "https://gitlab.com/nf-core/modules-test.git"
GITLAB_REPO = "nf-core"
GITLAB_DEFAULT_BRANCH = "main-restructure"
# Branch test stuff
GITLAB_BRANCH_TEST_BRANCH = "branch-tester-restructure"
GITLAB_BRANCH_TEST_OLD_SHA = "bce3f17980b8d1beae5e917cfd3c65c0c69e04b5"
GITLAB_BRANCH_TEST_NEW_SHA = "2f5f180f6e705bb81d6e7742dc2f24bf4a0c721e"


def with_temporary_folder(func):
    """
    Call the decorated funtion under the tempfile.TemporaryDirectory
    context manager. Pass the temporary directory name to the decorated
    function
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with tempfile.TemporaryDirectory() as tmpdirname:
            return func(*args, tmpdirname, **kwargs)

    return wrapper


def with_temporary_file(func):
    """
    Call the decorated funtion under the tempfile.NamedTemporaryFile
    context manager. Pass the opened file handle to the decorated function
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with tempfile.NamedTemporaryFile() as tmpfile:
            return func(*args, tmpfile, **kwargs)

    return wrapper


@contextmanager
def set_wd(path: Path):
    """Sets the working directory for this context.

    Arguments
    ---------

    path : Path
        Path to the working directory to be used iside this context.
    """
    start_wd = Path().absolute()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(start_wd)
