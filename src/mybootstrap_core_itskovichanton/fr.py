from contextlib import suppress
from dataclasses import dataclass
from typing import Protocol

import requests
from paprika import threaded, silent_catch
from src.mybootstrap_ioc_itskovichanton.ioc import bean


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

        with suppress(BaseException):
            requests.request("POST", self.url + "/postMsg",
                             data={'msg': a.msg, 'project': a.project, 'level': a.level})
