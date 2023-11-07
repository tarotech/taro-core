#  Sender, Listening
import abc
import json
import logging
from abc import abstractmethod
from json import JSONDecodeError

from tarotools.taro import util
from tarotools.taro.jobs.events import PHASE_LISTENER_FILE_EXTENSION, OUTPUT_LISTENER_FILE_EXTENSION
from tarotools.taro.jobs.instance import JobRunMetadata
from tarotools.taro.run import TerminationStatus, Phase
from tarotools.taro.socket import SocketServer

log = logging.getLogger(__name__)


def _listener_socket_name(ext):
    return util.unique_timestamp_hex() + ext


def _missing_field_txt(obj, missing):
    return f"event=[invalid_event] object=[{obj}] reason=[missing field: {missing}]"


def _read_metadata(req_body_json):
    event_metadata = req_body_json.get('event_metadata')
    if not event_metadata:
        raise ValueError(_missing_field_txt('root', 'event_metadata'))

    event_type = event_metadata.get('event_type')
    if not event_type:
        raise ValueError(_missing_field_txt('event_metadata', 'event_type'))

    instance_metadata = req_body_json.get('instance_metadata')
    if not instance_metadata:
        raise ValueError(_missing_field_txt('root', 'instance_metadata'))

    return event_type, JobRunMetadata.deserialize(instance_metadata)


class EventReceiver(SocketServer):

    def __init__(self, socket_name, id_match=None, event_types=()):
        super().__init__(socket_name, allow_ping=True)
        self.id_match = id_match
        self.event_types = event_types

    def handle(self, req_body):
        try:
            req_body_json = json.loads(req_body)
        except JSONDecodeError:
            log.warning(f"event=[invalid_json_event_received] length=[{len(req_body)}]")
            return

        try:
            event_type, instance_meta = _read_metadata(req_body_json)
        except ValueError as e:
            log.warning(e)
            return

        if (self.event_types and event_type not in self.event_types) or \
                (self.id_match and not self.id_match(instance_meta.id)):
            return

        self.handle_event(event_type, instance_meta, req_body_json.get('event'))

    @abstractmethod
    def handle_event(self, event_type, instance_meta, event):
        pass


class PhaseReceiver(EventReceiver):

    def __init__(self, id_match=None, phases=()):
        super().__init__(_listener_socket_name(PHASE_LISTENER_FILE_EXTENSION), id_match)
        self.phases = phases
        self.listeners = []

    def handle_event(self, _, instance_meta, event):
        new_phase = Phase.deserialize(event["new_phase"])

        if self.phases and new_phase not in self.phases:
            return

        previous_phase = Phase.deserialize(event['previous_phase'])
        changed = util.parse_datetime(event["changed"])
        termination_status = TerminationStatus[
            "termination_status"] if "termination_status" in event else TerminationStatus.NONE

        for listener in self.listeners:
            if isinstance(listener, InstancePhaseEventObserver):
                listener.state_update(instance_meta, previous_phase, new_phase, changed, termination_status)
            elif callable(listener):
                listener(instance_meta, previous_phase, new_phase, changed, termination_status)
            else:
                log.warning("event=[unsupported_phase_observer] observer=[%s]", listener)


class InstancePhaseEventObserver(abc.ABC):

    @abc.abstractmethod
    def state_update(self, instance_meta, previous_phase, new_phase, changed, termination_status):
        """
        This method is called when a job instance's transitioned to a new phase.

        :param instance_meta: job instance metadata
        :param previous_phase: phase before
        :param new_phase: new phase
        :param changed: timestamp of the transition
        :param termination_status: termination status of the new phase is TERMINAL
        """


class OutputReceiver(EventReceiver):

    def __init__(self, id_match=None):
        super().__init__(_listener_socket_name(OUTPUT_LISTENER_FILE_EXTENSION), id_match)
        self.listeners = []

    def handle_event(self, _, instance_meta, event):
        output = event['output']
        is_error = event['is_error']
        for listener in self.listeners:
            if isinstance(listener, OutputEventObserver):
                listener.output_event_update(instance_meta, output, is_error)
            elif callable(listener):
                listener(instance_meta, output, is_error)
            else:
                log.warning("event=[unsupported_output_event_observer] observer=[%s]", listener)


class OutputEventObserver(abc.ABC):

    @abc.abstractmethod
    def output_event_update(self, instance_meta, output, is_error):
        """
        Executed when new output line is available.

        :param instance_meta: data about the job instance producing the output
        :param output: job instance output text
        :param is_error: True when it is an error output
        """
