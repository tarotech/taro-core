"""
Tests :mod:`app` module
Command: stop
"""
import pytest

from taro.execution import ExecutionState
from test.util import run_app, run_app_as_process, run_wait


def test_stop_must_specify_job(capsys):
    with pytest.raises(SystemExit):
        run_app('stop')


def test_stop(capsys):
    run_w = run_wait(ExecutionState.RUNNING, 2)
    stop_w = run_wait(ExecutionState.STOPPED)
    p1 = run_app_as_process('exec --id to_stop sleep 5', daemon=True)
    p2 = run_app_as_process('exec --id to_keep sleep 5', daemon=True)
    run_w.join()  # Wait for both exec to run

    run_app('stop to_stop')

    stop_w.join(1)
    assert not p1.is_alive()
    assert p2.is_alive()


def test_more_jobs_require_all_flag(capsys):
    pw = run_wait(ExecutionState.RUNNING, 2)
    p1 = run_app_as_process('exec --id j1 sleep 5', daemon=True)
    p2 = run_app_as_process('exec --id j1 sleep 5', daemon=True)
    pw.join()  # Wait for both exec to run

    run_app('stop j1')

    output = capsys.readouterr().out
    assert 'more than one job' in output
    assert p1.is_alive()
    assert p2.is_alive()