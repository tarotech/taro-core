"""
This module contains the default implementation of the `RunnableJobInstance` interface from the `inst` module.
A job instance is executed by calling the `run` method. The method call returns after the instance terminates.
It is possible to register observers directly in the module. These are then notified about events from all
job instances. An alternative for multi-observing is to use the featured context from the `featurize` module.

This implementation adds a few features not explicitly defined in the interface:

Coordination
------------
Job instances can be coordinated with each other or with any external logic. Coordinated instances are typically
affected in ways that might require them to wait for a condition, or they might be discarded if necessary. The
coordination logic heavily relies on global synchronization.

Some examples of coordination include:
  - Pending latch:
    Several instances can be started simultaneously by sending a release request to the corresponding group.
  - Serial execution:
    Instances of the same job or group execute sequentially.
  - Parallel execution limit:
    Only N number of instances can execute in parallel.
  - Overlap forbidden:
    Parallel execution of instances of the same job can be restricted.
  - Dependency:
    An instance can start only if another specific instance is active.

Global Synchronization
----------------------
For coordination to function correctly, a mechanism that allows the coordinator to utilize some form of
shared lock is often essential. Job instances attempt to acquire this lock each time the coordination logic runs.
The lock remains held when the execution state changes. This is crucial because the current state of coordinated
instances often dictates the coordination action, and using a lock ensures that the 'check-then-act' sequence
on the execution states is atomic, preventing race conditions.


IMPLEMENTATION NOTES

State lock
----------
1. Atomic update of the job instance state (i.e. error object + failure state)
2. Consistent execution state notification order
3. No race condition on state observer notify on register

"""

import logging
from typing import Optional

from tarotools.taro import util, PhaseTransitionObserver
from tarotools.taro.jobs.instance import JobInstance, JobRun, JobRunId, JobRunMetadata, JobInstSnapshot
from tarotools.taro.run import Phaser, Flag, Fault, PhaseRun
from tarotools.taro.status import StatusObserver
from tarotools.taro.util.observer import DEFAULT_OBSERVER_PRIORITY, CallableNotification, ObservableNotification

log = logging.getLogger(__name__)


def log_observer_error(observer, args, exc):
    log.error("event=[observer_error] observer=[%s], args=[%s] error_type=[%s], error=[%s]", observer, args, exc)


_transition_callback = CallableNotification(error_hook=log_observer_error)
_status_observers = CallableNotification(error_hook=log_observer_error)
_warning_observers = CallableNotification(error_hook=log_observer_error)


class RunnerJobInstance(JobInstance):

    def __init__(self, job_id, phases, *, run_id=None, instance_id_gen=util.unique_timestamp_hex, **user_params):
        self._instance_id = instance_id_gen()
        self._job_run_id = JobRunId(job_id, run_id or self._instance_id)
        parameters = ()  # TODO
        self._metadata = JobRunMetadata(self._job_run_id, parameters, user_params)
        self._phaser = Phaser(phases)
        self._tracking = None  # TODO The output fields below will be moved to the tracker
        # self._last_output = deque(maxlen=10)  # TODO Max len configurable
        # self._error_output = deque(maxlen=1000)  # TODO Max len configurable
        self._transition_notification = ObservableNotification[PhaseTransitionObserver](error_hook=log_observer_error)
        self._status_notification = ObservableNotification[StatusObserver](error_hook=log_observer_error)

        self._phaser.transition_hook = self._transition_hook

    def _log(self, event: str, msg: str = '', *params):
        return ("event=[{}] instance=[{}] " + msg).format(event, self._job_run_id, *params)

    @property
    def instance_id(self):
        return self._instance_id

    @property
    def metadata(self):
        return self._metadata

    @property
    def lifecycle(self):
        return self._phaser.create_run_snapshot().lifecycle

    @property
    def tracking(self):
        return self._tracking

    @property
    def run_failure(self):
        return self._phaser.create_run_snapshot().run_failure

    @property
    def run_error(self) -> Optional[Fault]:
        return self._phaser.create_run_snapshot().run_error

    @property
    def status_observer(self):
        return self._status_notification.observer_proxy

    def create_snapshot(self) -> JobInstSnapshot:
        run_snapshot = self._phaser.create_run_snapshot()
        job_run = JobRun(
            self.metadata,
            run_snapshot.phases,
            run_snapshot.lifecycle,
            self.tracking.copy(),
            run_snapshot.termination_status,
            run_snapshot.run_failure,
            run_snapshot.run_error)

        return JobInstSnapshot(self._instance_id, job_run)

    def run(self):
        observer_proxy = self._status_notification.observer_proxy
        for phase_step in self._phaser.phases:
            phase_step.add_status_observer(observer_proxy)

        try:
            self._phaser.run()
        finally:
            for phase_step in self._phaser.phases:
                phase_step.remove_status_observer(observer_proxy)

    def stop(self):
        """
        Cancel not yet started execution or stop started execution.
        Due to synchronous design there is a small window when an execution can be stopped before it is started.
        All execution implementations must cope with such scenario.
        """
        self._phaser.stop()

    def interrupted(self):
        """
        Cancel not yet started execution or interrupt started execution.
        Due to synchronous design there is a small window when an execution can be interrupted before it is started.
        All execution implementations must cope with such scenario.
        """
        self._phaser.stop()  # TODO Interrupt

    def add_observer_phase_transition(self, observer, priority=DEFAULT_OBSERVER_PRIORITY, notify_on_register=False):
        if notify_on_register:
            def add_and_notify_callback(*args):
                self._transition_notification.add_observer(observer)
                observer.new_phase(self._phaser.create_run_snapshot(), *args)

            self._phaser.execute_transition_hook_safely(add_and_notify_callback)
        else:
            self._transition_notification.add_observer(observer)

    def remove_observer_phase_transition(self, callback):
        self._transition_notification.remove_observer(callback)

    def _transition_hook(self, prev_phase: PhaseRun, new_phase: PhaseRun, ordinal):
        """Executed under phaser transition lock"""
        job_run = self.create_snapshot()

        if job_run.run_error:
            log.error(self._log('unexpected_error', "error_type=[{}] reason=[{}]",
                                job_run.run_error.fault_type, job_run.run_error.reason))
        elif job_run.run_failure:
            log.warning(self._log('run_failed', "error_type=[{}] reason=[{}]",
                                  job_run.run_error.fault_type, job_run.run_error.reason))

        if job_run.termination_status.has_flag(Flag.NONSUCCESS):
            level = logging.WARN
        else:
            level = logging.INFO
        log.log(level, self._log('phase_changed', "prev_phase=[{}] new_phase=[{}] ordinal=[{}]",
                                 prev_phase.phase_name, new_phase.phase_name, ordinal))

        self._transition_notification.observer_proxy.new_phase(job_run, prev_phase, new_phase, ordinal)

    def add_observer_status(self, observer, priority=DEFAULT_OBSERVER_PRIORITY):
        self._status_notification.add_observer(observer, priority)

    def remove_observer_status(self, observer):
        self._status_notification.remove_observer(observer)


def register_transition_callback(observer, priority=DEFAULT_OBSERVER_PRIORITY):
    global _transition_callback
    _transition_callback.add_observer(observer, priority)


def deregister_transition_callback(observer):
    global _transition_callback
    _transition_callback.remove_observer(observer)


def register_status_observer(observer, priority=DEFAULT_OBSERVER_PRIORITY):
    global _status_observers
    _status_observers.add_observer(observer, priority)


def deregister_status_observer(observer):
    global _status_observers
    _status_observers.remove_observer(observer)
