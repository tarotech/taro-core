from unittest.mock import patch

import pytest
from webtest import TestApp

import taros
from taro.client import MultiResponse
from taro.jobs import repo
from taro.jobs.inst import JobInfoList
from taro.jobs.job import JobStats
from taro.jobs.repo import JobRepositoryFile
from taro.test.execution import lc_running
from taro.test.job import i
from test.taro_test_util import create_custom_test_config, remove_custom_test_config


@pytest.fixture
def web_app():
    test_file_jobs = {
        'jobs': [
            {
                'id': 'j1',
                'properties': {'prop': 'value1'}
            },
            {
                'id': 'j2',
                'properties': {'prop': 'value2'}
            },
            {
                'id': 'j3',
                'properties': {'prop': 'value3'}
            }
        ]
    }
    test_file_jobs_path = create_custom_test_config('jobs.yaml', test_file_jobs)
    repo.add_repo(JobRepositoryFile(test_file_jobs_path))

    yield TestApp(taros.app.api)

    remove_custom_test_config('jobs.yaml')


def test_no_such_job(web_app):
    assert web_app.get('/jobs/no_such_job', expect_errors=True).status_int == 404


def test_empty_jobs(web_app):
    test_file_jobs_path = create_custom_test_config('jobs.yaml', {})
    repo.add_repo(JobRepositoryFile(test_file_jobs_path))

    resp = web_app.get('/jobs')
    assert resp.status_int == 200
    assert len(resp.json["_embedded"]["jobs"]) == 0


@patch('taro.client.read_jobs_info', return_value=MultiResponse([i('active_job_1'), i('j1')], []))
@patch('taro.persistence.read_stats', return_value=JobInfoList([JobStats('ended_job_1'), JobStats('j2')]))
def test_jobs_all_default_repos(_, __, web_app):
    resp = web_app.get('/jobs')
    assert resp.status_int == 200

    jobs = resp.json["_embedded"]["jobs"]
    assert len(jobs) == 5

    id_2_job = {job["id"]: job for job in jobs}
    assert 'active_job_1' in id_2_job
    assert id_2_job["j1"]["properties"]["prop"] == 'value1'
    assert 'ended_job_1' in id_2_job
    assert id_2_job["j2"]["properties"]["prop"] == 'value2'
    assert id_2_job["j3"]["properties"]["prop"] == 'value3'


def test_empty_instances(web_app):
    resp = web_app.get('/instances')
    assert resp.status_int == 200
    assert len(resp.json["_embedded"]["instances"]) == 0


def test_empty_finished_instances(web_app):
    resp = web_app.get('/instances?finished')
    assert resp.status_int == 200
    assert len(resp.json["_embedded"]["instances"]) == 0


@patch('taro.client.read_jobs_info', return_value=MultiResponse([i('j1', lifecycle=lc_running())], []))
def test_job_def_included_for_instance(_, web_app):
    resp = web_app.get('/instances')
    assert resp.status_int == 200
    assert len(resp.json["_embedded"]["instances"]) == 1
    assert len(resp.json["_embedded"]["jobs"]) == 1
    assert resp.json["_embedded"]["jobs"][0]["properties"]["prop"] == 'value1'
