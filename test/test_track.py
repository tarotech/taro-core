from tarotools.taro.track import TrackedOperation, TaskTrackerMem, TrackedProgress
from tarotools.taro.util import parse_datetime


def test_add_event():
    tracker = TaskTrackerMem('task')
    tracker.event('e1')
    tracker.event('e2')

    assert tracker.tracked_task.current_event[0] == 'e2'


def test_operation_updates():
    tracker = TaskTrackerMem('task')
    tracker.operation('op1').progress.update(1, 10, 'items')

    op1 = tracker.tracked_task.operations[0]
    assert op1.name == 'op1'
    assert op1.progress.completed == 1
    assert op1.progress.total == 10
    assert op1.progress.unit == 'items'


def test_operation_incr_update():
    tracker = TaskTrackerMem('task')
    tracker.operation('op1').progress.update(1, increment=True)

    op1 = tracker.tracked_task.operations[0]
    assert op1.name == 'op1'
    assert op1.progress.completed == 1
    assert op1.progress.total is None
    assert op1.progress.unit == ''

    tracker.operation('op1').progress.update(3, 5, increment=True)
    tracker.operation('op2').progress.update(0, 10)
    op1 = tracker.tracked_task.operations[0]
    assert op1.progress.completed == 4
    assert op1.progress.total == 5

    op2 = tracker.tracked_task.operations[1]
    assert op2.name == 'op2'
    assert op2.progress.total == 10


def test_subtask():
    tracker = TaskTrackerMem('main')
    tracker.task('s1').event('e1')
    tracker.task('s1').operation('01').progress.update(2)
    tracker.task(2).event('e2')

    tracked_task = tracker.tracked_task
    assert tracked_task.current_event is None
    assert tracked_task.subtasks[0].current_event[0] == 'e1'
    assert tracked_task.subtasks[0].operations[0].name == '01'
    assert tracked_task.subtasks[1].current_event[0] == 'e2'


def test_operation_str():
    empty_op = TrackedOperation('name', None, None, None, True)
    assert str(empty_op) == 'name'

    assert '25/100 files (25%)' == str(TrackedOperation(None, TrackedProgress(25, 100, 'files'), None, None, True))
    assert 'Op 25/100 files (25%)' == str(TrackedOperation('Op', TrackedProgress(25, 100, 'files'), None, None, True))


def test_progress_str():
    progress = TrackedProgress(25, 100, 'files')
    assert str(progress) == '25/100 files (25%)'

    progress = TrackedProgress(None, 100, 'files')
    assert str(progress) == '?/100 files'

    progress = TrackedProgress(20, None, 'files')
    assert str(progress) == '20 files'


def test_task_str():
    tracker = TaskTrackerMem('task1')
    assert str(tracker.tracked_task) == 'task1:'
    tracker.event('e1', parse_datetime('2023-01-01T00:00:00'))
    assert str(tracker.tracked_task) == 'task1: e1'
    tracker.event('e2', parse_datetime('2023-01-01T01:00:00'))
    assert str(tracker.tracked_task) == 'task1: e2'
    tracker.operation('downloading')
    tracker.reset_current_event()
    assert str(tracker.tracked_task) == 'task1: downloading'
    tracker.operation('downloading').progress.set_unit('files')
    assert str(tracker.tracked_task) == 'task1: downloading ? files'
    tracker.operation('uploading')
    assert str(tracker.tracked_task) == 'task1: downloading ? files | uploading'
    tracker.operation('downloading').deactivate()
    assert str(tracker.tracked_task) == 'task1: uploading'
    tracker.event('e3', parse_datetime('2023-01-01T02:00:00'))
    assert str(tracker.tracked_task) == 'task1: e3 | uploading'
    tracker.task('sub-zero').operation('freezing')
    assert str(tracker.tracked_task) == 'task1: e3 | uploading / sub-zero: freezing'
    tracker.deactivate()
    assert str(tracker.tracked_task) == 'sub-zero: freezing'
    tracker.task('scorpion').event('burning', parse_datetime('2023-01-01T05:00:00'))
    assert str(tracker.tracked_task) == 'sub-zero: freezing / scorpion: burning'
    tracker.task('scorpion').result('fatality')
    assert str(tracker.tracked_task) == 'sub-zero: freezing / scorpion: fatality'
