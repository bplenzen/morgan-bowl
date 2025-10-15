import os
from collections.abc import Callable
from contextlib import contextmanager
from typing import ContextManager

import pytest


@contextmanager
def temporary_env(overrides: dict[str, str]):
    original = {key: os.environ.get(key) for key in overrides}
    os.environ.update(overrides)
    try:
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@pytest.fixture
def env_override() -> Callable[[dict[str, str]], ContextManager[None]]:
    def _apply(overrides: dict[str, str]):
        return temporary_env(overrides)

    return _apply
