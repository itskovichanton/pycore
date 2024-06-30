import json
from typing import Protocol, Callable, Any

from src.mybootstrap_core_itskovichanton.redis_service import RedisService
from src.mybootstrap_core_itskovichanton.utils import to_dict_deep
from src.mybootstrap_ioc_itskovichanton.ioc import bean
from src.mybootstrap_pyauth_itskovichanton.backend.auth import Authentificator
from src.mybootstrap_pyauth_itskovichanton.entities import User

from src.mbulak_tools.db import DBService


class GetInfoUsecase(Protocol):

    def info(self) -> dict:
        ...

    def add_info(self, level: str, name: str, msg: Callable[[str, str], Any]):
        ...


@bean
class GetInfoUsecaseImpl(GetInfoUsecase):

    def init(self, **kwargs):
        self._infos = {}

    def add_info(self, level: str, name: str, msg: Callable[[str, str], Any]):
        infos = self._infos.get(level)
        if not infos:
            self._infos[level] = {}
        self._infos[level][name] = msg

    def info(self) -> dict:
        def calc_msg(route, v):
            if callable(v):
                v = v(*route)
            return v

        return to_dict_deep(self._infos, value_mapper=calc_msg)
