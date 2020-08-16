# -*- coding: utf-8 -*-
"""Module defines common test fixtures."""
from logging import getLogger

from cement import fs

import pytest


@pytest.fixture(scope="session")
def logger():
    """Provide logger instance."""
    logger = getLogger(__name__)

    return logger


@pytest.fixture(scope="function")
def tmp(request):
    """Provide temporary directory.

    Create a `Tmp` object that generates a unique temporary directory, and file
    for each test function that requires it.
    """
    t = fs.Tmp()
    yield t
    t.remove()
