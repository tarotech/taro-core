"""
Execution framework defines an abstraction for an execution of a task.
It consists of:
 1. Possible states of execution
 2. A structure for conveying of error conditions
 3. An interface for implementing various types of executions
"""

import abc
import datetime
from collections import OrderedDict
from enum import IntEnum
from typing import Tuple, List, Iterable


class ExecutionState(IntEnum):
    NONE = 0
    CREATED = 1
    WAITING = 2
    RUNNING = 3
    TRIGGERED = 4  # When request to start job was sent, but confirmation has not been (or cannot be) received
    STARTED = 5
    COMPLETED = 6
    CANCELLED = 7
    STOPPED = 8
    START_FAILED = 9
    INTERRUPTED = 10
    FAILED = 11
    ERROR = 12

    def is_before_execution(self):
        return self <= ExecutionState.WAITING

    def is_executing(self):
        return ExecutionState.RUNNING <= self <= ExecutionState.STARTED

    def is_terminal(self) -> bool:
        return self >= ExecutionState.COMPLETED

    def is_failure(self) -> bool:
        return self >= ExecutionState.START_FAILED


class ExecutionError(Exception):

    @classmethod
    def from_unexpected_error(cls, e: Exception):
        return cls("Unexpected error", ExecutionState.ERROR, unexpected_error=e)

    def __init__(self, message: str, exec_state: ExecutionState, unexpected_error: Exception = None, **kwargs):
        if not exec_state.is_failure():
            raise ValueError('exec_state must be a failure', exec_state)
        super().__init__(message)
        self.message = message
        self.exec_state = exec_state
        self.unexpected_error = unexpected_error
        self.params = kwargs


class Execution(abc.ABC):

    @abc.abstractmethod
    def is_async(self) -> bool:
        """
        SYNCHRONOUS TASK
            - finishes after the call of the execute() method
            - execution state is changed to RUNNING before the call of the execute() method

        ASYNCHRONOUS TASK
            - need not to finish after the call of the execute() method
            - execution state is changed to TRIGGER before the call of the execute() method

        :return: whether this execution is asynchronous
        """

    @abc.abstractmethod
    def execute(self) -> ExecutionState:
        """
        Executes a task

        :return: state after the execution of this method
        :raises ExecutionError: when execution failed
        :raises Exception: on unexpected failure
        """

    @abc.abstractmethod
    def progress(self):
        """
        If progress monitoring is not supported then this method must return None

        :return: Current progress of the execution or None
        """

    @abc.abstractmethod
    def stop(self):
        """
        If not yet executed: Do not execute
        If already executing: Stop running execution GRACEFULLY
        If execution finished: Ignore
        """

    @abc.abstractmethod
    def interrupt(self):
        """
        If not yet executed: Do not execute
        If already executing: Stop running execution IMMEDIATELY
        If execution finished: Ignore
        """


class ExecutionLifecycle:

    def __init__(self, *state_changes: Tuple[ExecutionState, datetime.datetime]):
        self._state_changes: OrderedDict[ExecutionState, datetime.datetime] = OrderedDict(state_changes)

    def state(self):
        return next(reversed(self._state_changes.keys()), ExecutionState.NONE)

    def states(self) -> List[ExecutionState]:
        return list(self._state_changes.keys())

    def state_changes(self) -> Iterable[Tuple[ExecutionState, datetime.datetime]]:
        return ((state, changed) for state, changed in self._state_changes.items())

    def changed(self, state: ExecutionState) -> datetime.datetime:
        return self._state_changes[state]

    def last_changed(self):
        return next(reversed(self._state_changes.values()), None)

    def execution_start(self) -> datetime.datetime:
        return next((changed for state, changed in self._state_changes.items() if state.is_executing()), None)


class ExecutionLifecycleManagement(ExecutionLifecycle):

    def __init__(self, *state_changes: Tuple[ExecutionState, datetime.datetime]):
        super().__init__(*state_changes)

    def set_state(self, new_state) -> bool:
        if not new_state or new_state == ExecutionState.NONE or self.state() == new_state:
            return False
        else:
            self._state_changes[new_state] = datetime.datetime.now(datetime.timezone.utc)
            return True
