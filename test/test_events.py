from datetime import datetime

from tarotools.taro import ExecutionState
from tarotools.taro.jobs.events import StateDispatcher, OutputDispatcher
from tarotools.taro.listening import StateReceiver, OutputReceiver
from tarotools.taro.test.inst import TestJobInstance
from tarotools.taro.test.observer import GenericObserver


def test_state_dispatching():
    dispatcher = StateDispatcher()
    receiver = StateReceiver()
    observer = GenericObserver()
    receiver.listeners.append(observer)
    receiver.start()
    try:
        dispatcher.new_instance_state(
            TestJobInstance('j1').create_snapshot(),
            ExecutionState.NONE,
            ExecutionState.CREATED,
            datetime(2023, 8, 6))
    finally:
        dispatcher.close()
        receiver.close()

    instance_meta, prev_state, new_state, changed = observer.updates.get(timeout=2)
    assert instance_meta.id.job_id == 'j1'
    assert prev_state == ExecutionState.NONE
    assert new_state == ExecutionState.CREATED
    assert changed == datetime(2023, 8, 6)


def test_output_dispatching():
    dispatcher = OutputDispatcher()
    receiver = OutputReceiver()
    observer = GenericObserver()
    receiver.listeners.append(observer)
    receiver.start()
    try:
        dispatcher.new_instance_output(TestJobInstance('j1').create_snapshot(), "Happy Mushrooms", True)
    finally:
        dispatcher.close()
        receiver.close()

    instance_meta, new_output, is_error = observer.updates.get(timeout=2)
    assert instance_meta.id.job_id == 'j1'
    assert new_output == "Happy Mushrooms"
    assert is_error