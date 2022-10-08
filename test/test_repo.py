"""
Tests :mod:`jobs.repo` module
Description: Jobs file repository tests
"""

import pytest

from taro import paths
from taro.jobs import repo
from test.taro_test_util import create_custom_test_config, remove_custom_test_config


@pytest.fixture(autouse=True)
def remove_config_if_created():
    yield
    remove_custom_test_config(paths.JOBS_FILE)


def test_defaults():
    create_custom_test_config(paths.JOBS_FILE, repo.JOBS_FILE_CONTENT)
    example_job = repo.JOBS_FILE_CONTENT['jobs'][0]
    assert repo.get_job(example_job['job_id']).properties == example_job['properties']