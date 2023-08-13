from collections import Counter

from tarotools.taro import ExecutionState, Flag
from tarotools.taro.jobs.inst import IntervalCriteria, LifecycleEvent, StateCriteria
from tarotools.taro.test.inst import TestJobInstance


def test_interval_utc_conversion():
    c = IntervalCriteria.to_utc(LifecycleEvent.CREATED, from_val='2023-11-10T09:00+02:00', to_val=None)
    assert c.from_dt.hour == 7


def test_state_criteria():
    inst = TestJobInstance('skipped', '', ExecutionState.SKIPPED)
    inst.warnings = Counter(['error_output'])
    matching1 = StateCriteria(flag_groups=[{Flag.SUCCESS}, {Flag.UNEXECUTED, Flag.NONSUCCESS}])
    not_matching1 = StateCriteria(flag_groups=[{Flag.SUCCESS}, {Flag.UNEXECUTED, Flag.ABORTED}])

    matching2 = StateCriteria(flag_groups=[{Flag.UNEXECUTED}], warning=True)
    not_matching2 = StateCriteria(flag_groups=[{Flag.UNEXECUTED}], warning=False)

    assert matching1(inst)
    assert not not_matching1(inst)
    assert matching2(inst)
    assert not not_matching2(inst)
