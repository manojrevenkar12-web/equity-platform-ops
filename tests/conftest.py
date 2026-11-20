import pytest

from epo.config import load, world_config


@pytest.fixture(scope="session")
def cfg() -> dict:
    c = world_config()
    c["weeks"] = 3
    return c


@pytest.fixture(scope="session")
def platform() -> dict:
    return load("platform")


@pytest.fixture(scope="session")
def guard_cfg() -> dict:
    return load("guard")
