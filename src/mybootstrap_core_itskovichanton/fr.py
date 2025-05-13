from contextlib import suppress
from dataclasses import dataclass
from typing import Protocol

import requests
from paprika import threaded
from src.mybootstrap_ioc_itskovichanton.ioc import bean

from src.mybootstrap_core_itskovichanton.utils import to_dict_deep, trim_string, silent_catch


@dataclass
class FRConfig:
    url: str
    developer_id: str


@dataclass
class Post:
    project: str
    msg: str
    level: int


class FRService(Protocol):

    def send(self, a: Post):
        """Send post to fr"""


@bean(url=("fr.url", str, None), developer_id=("fr.developer_id", str, None))
class FRServiceImpl(FRService):

    @threaded
    @silent_catch
    def send(self, a: Post):
        if not self.url:
            return

        if not isinstance(a.msg, dict):
            a.msg = to_dict_deep(a.msg)

        a.msg = trim_string(str(a.msg), 4000)

        with suppress(BaseException):
            requests.request("POST", self.url + "/postMsg",
                             data={'msg': a.msg, 'project': a.project, 'level': a.level})
