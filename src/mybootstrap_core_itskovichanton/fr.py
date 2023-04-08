from contextlib import suppress
from dataclasses import dataclass
from typing import Protocol

import requests
from paprika import threaded
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


@bean(config=("fr", FRConfig))
class FRServiceImpl(FRService):

    @threaded
    def send(self, a: Post):
        if self.config is None:
            return
        with suppress(BaseException):
            requests.request("POST", self.config.url + "/postMsg",
                             data={'msg': a.msg, 'project': a.project, 'level': a.level})
