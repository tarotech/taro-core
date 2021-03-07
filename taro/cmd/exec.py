import logging
import signal

from taro import cnf, ExecutionState, PluginBase, warning
from taro import log
from taro import persistence
from taro.api import Server
from taro.listening import StateDispatcher, OutputDispatcher
from taro.program import ProgramExecution
from taro.runner import RunnerJobInstance
from taro.test.execution import TestExecution

logger = logging.getLogger(__name__)

EXT_PLUGIN_MODULE_PREFIX = 'taro_'


def run(args):
    if args.dry_run:
        execution = TestExecution(args.dry_run)
    else:
        execution = ProgramExecution([args.command] + args.arg, read_output=not args.bypass_output)
    execute(execution, args)


def execute(execution, args):
    cnf.init(args)
    log.init()
    persistence.init()

    job_id = args.id or " ".join([args.command] + args.arg)
    job_instance = RunnerJobInstance(job_id, execution, no_overlap=args.no_overlap)
    execution.add_output_observer(job_instance)
    term = Term(job_instance)
    signal.signal(signal.SIGTERM, term.terminate)
    signal.signal(signal.SIGINT, term.interrupt)
    state_dispatcher = StateDispatcher()
    job_instance.add_state_observer(state_dispatcher)
    output_dispatcher = OutputDispatcher()
    job_instance.add_output_observer(output_dispatcher)
    for plugin in PluginBase.load_plugins(EXT_PLUGIN_MODULE_PREFIX,
                                          cnf.config.plugins).values():  # TODO to plugin module
        try:
            plugin.new_job_instance(job_instance)
        except BaseException as e:
            logger.warning("event=[plugin_failed] reason=[exception_on_new_job_instance] detail=[%s]", e)

    if args.warn:
        warning.setup_checking(job_instance, *args.warn)

    pending_latch = \
        PendingValueLatch(args.pending, job_instance.create_latch(ExecutionState.PENDING)) if args.pending else None
    api = Server(job_instance, pending_latch)
    api_started = api.start()  # Starts a new thread
    if not api_started:
        logger.warning("event=[api_not_started] message=[Interface for managing the job failed to start]")
    try:
        job_instance.run()
    finally:
        api.stop()
        state_dispatcher.close()
        output_dispatcher.close()
        persistence.close()


class Term:

    def __init__(self, job_instance):
        self.job_instance = job_instance

    def terminate(self, _, __):
        logger.warning('event=[terminated_by_signal]')
        self.job_instance.interrupt()

    def interrupt(self, _, __):
        logger.warning('event=[interrupted_by_keyboard]')
        self.job_instance.interrupt()  # TODO handle repeated signal


class PendingValueLatch:

    def __init__(self, value, latch):
        self.value = value
        self.latch = latch

    def release(self, value):
        if self.value == value:
            self.latch()
            return True
        else:
            return False
