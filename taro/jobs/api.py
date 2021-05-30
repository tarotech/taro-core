import logging
from typing import Tuple

from taro import dto
from taro.socket import SocketServer

log = logging.getLogger(__name__)

API_FILE_EXTENSION = '.api'


def _create_socket_name(job_info):
    return job_info.instance_id + API_FILE_EXTENSION


def _resp(code: int, job_instance: Tuple[str, str], data):
    return {"resp": {"code": code}, "job_id": job_instance[0], "instance_id": job_instance[1], "data": data}


def _resp_err(code: int, job_instance: Tuple[str, str], error: str):
    if 400 > code >= 600:
        raise ValueError("Error code must be 4xx or 5xx")
    return {"resp": {"code": code}, "job_id": job_instance[0], "instance_id": job_instance[1], "error": error}


class Server(SocketServer):

    def __init__(self, job_instance, latch_release):
        super().__init__(_create_socket_name(job_instance))
        self._job_instance = job_instance
        self._latch_release = latch_release

    def handle(self, req_body):
        job_inst = (self._job_instance.job_id, self._job_instance.instance_id)

        if 'req' not in req_body:
            return _resp_err(422, job_inst, "missing_req")
        if 'api' not in req_body['req']:
            return _resp_err(422, job_inst, "missing_req_api")

        inst_filter = req_body.get('instance')
        if inst_filter and not self._job_instance.create_info().matches(inst_filter):
            return _resp(412, job_inst, {"reason": "instance_not_matching"})

        if req_body['req']['api'] == '/job':
            info_dto = dto.to_info_dto(self._job_instance.create_info())
            return _resp(200, job_inst, {"job_info": info_dto})

        if req_body['req']['api'] == '/release':
            if 'data' not in req_body:
                return _resp_err(422, job_inst, "missing_data")
            if 'pending' not in req_body['data']:
                return _resp_err(422, job_inst, "missing_data_field:pending")

            if self._latch_release:
                released = self._latch_release.release(req_body.get('data').get('pending'))
            else:
                released = False
            return _resp(200, job_inst, {"released": released})

        if req_body['req']['api'] == '/stop':
            self._job_instance.stop()
            return _resp(200, job_inst, {"result": "stop_performed"})

        if req_body['req']['api'] == '/interrupt':
            self._job_instance.interrupt()
            return _resp(200, job_inst, {"result": "interrupt_performed"})

        if req_body['req']['api'] == '/tail':
            return _resp(200, job_inst, {"tail": self._job_instance.last_output})

        return _resp_err(404, job_inst, "req_api_not_found")