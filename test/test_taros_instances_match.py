import datetime
from datetime import timedelta
from unittest.mock import patch

import bottle
import pytest
from webtest import TestApp

import taros
from taro.client import MultiResponse
from taro.jobs import persistence
from taro.jobs.job import Job
from taro.test.execution import lc_completed, lc_failed, lc_stopped
from taro.test.job import i
from taro.test.persistence import TestPersistence
from taro.util import MatchingStrategy


@pytest.fixture
def web_app():
    first_created = datetime.datetime(2023, 6, 22, 0, 0)
    failed_1 = i('failed_1', lifecycle=lc_failed(start_date=first_created))
    completed_2 = i('completed_2', 'oldest', lifecycle=lc_completed(start_date=first_created + timedelta(minutes=10), term_delta=4))
    completed_1_old = i('completed_1', 'old', lifecycle=lc_completed(start_date=first_created + timedelta(minutes=11), term_delta=3))
    completed_1_new = i('completed_1', 'new', lifecycle=lc_completed(start_date=first_created + timedelta(minutes=12), term_delta=2))
    stopped_1 = i('stopped_1', lifecycle=lc_stopped(start_date=first_created + timedelta(hours=4)))

    bottle.debug(True)

    with TestPersistence():
        persistence.store_instances(completed_1_new, completed_2, completed_1_old, failed_1, stopped_1)
        yield TestApp(taros.app.api)

    bottle.debug(False)


@pytest.fixture
def client_mock():
    with patch('taro.client.read_jobs_info', return_value=MultiResponse([], [])) as client_mock:
        yield client_mock


def assert_inst(resp, *job_ids):
    assert len(resp.json["_embedded"]["instances"]) == len(job_ids)
    assert [inst["metadata"]["id"]["job_id"] for inst in resp.json["_embedded"]["instances"]] == list(job_ids)


@patch('taro.repo.read_jobs', return_value=[Job('stopped_1', {'p1': 'v1'})])
def test_job_property_filter(_, web_app, client_mock):
    assert_inst(web_app.get('/instances?include=all&job_property=p1:v0'))  # Assert empty

    assert_inst(web_app.get('/instances?include=finished&job_property=p1:v1'), 'stopped_1')

    assert_inst(web_app.get('/instances?include=all&job_property=p1:v1'), 'stopped_1')
    assert client_mock.call_args[0][0].jobs == ['stopped_1']


def test_job_filter(web_app, client_mock):
    assert_inst(web_app.get('/instances?include=finished&job=completed_1'), 'completed_1', 'completed_1')
    assert_inst(web_app.get('/instances?include=all&job=completed_1'), 'completed_1', 'completed_1')
    assert client_mock.call_args_list[-1].args[0].jobs == ['completed_1']

def test_id_filter_job(web_app, client_mock):
    assert_inst(web_app.get('/instances?include=finished&id=stop'), 'stopped_1')
    assert_inst(web_app.get('/instances?include=all&id=stop'), 'stopped_1')

    id_criteria = client_mock.call_args_list[-1].args[0].id_criteria[0]
    assert id_criteria.job_id == 'stop'
    assert id_criteria.instance_id == 'stop'
    assert id_criteria.strategy == MatchingStrategy.PARTIAL

def test_id_filter_instance(web_app, client_mock):
    assert_inst(web_app.get('/instances?include=finished&id=old'), 'completed_1', 'completed_2')
    assert_inst(web_app.get('/instances?include=all&id=old'), 'completed_1', 'completed_2')

    id_criteria = client_mock.call_args_list[-1].args[0].id_criteria[0]
    assert id_criteria.job_id == 'old'
    assert id_criteria.instance_id == 'old'
    assert id_criteria.strategy == MatchingStrategy.PARTIAL