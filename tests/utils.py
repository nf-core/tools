#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper functions for tests
"""

import functools
import tempfile

OLD_TRIMGALORE_SHA = "20d8250d9f39ddb05dfb437603aaf99b5c0b2b41"
GITLAB_URL = "https://gitlab.com/nf-core/modules-test.git"
GITLAB_REPO = "nf-core/modules-test"
GITLAB_DEFAULT_BRANCH = "main"
# Branch test stuff
GITLAB_BRANCH_TEST_BRANCH = "branch-tester"
GITLAB_BRANCH_TEST_OLD_SHA = "eb4bc244de7eaef8e8ff0d451e4ca2e4b2c29821"
GITLAB_BRANCH_TEST_NEW_SHA = "e43448a2cc17d59e085c4d3f77489af5a4dcc26d"


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
