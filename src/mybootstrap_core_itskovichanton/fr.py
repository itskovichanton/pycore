from contextlib import suppress
from dataclasses import dataclass
from typing import Protocol

from httpx import AsyncClient

from src.mybootstrap_core_itskovichanton.ioc import bean


@dataclass
class FRConfig:
    url: str
    developer_id: int


@dataclass
class Post:
    project: str
    msg: str
    level: int


class FRService(Protocol):

    async def send(self, a: Post):
        """Send post to fr"""


@bean(config=('fr', FRConfig))
class FRServiceImpl(FRService):
    http_client: AsyncClient

    async def send(self, a: Post):
        if self.config is None:
            return
        with suppress(BaseException):
            await self.http_client.post(self.config.url + "/postMsg",
                                        data={'msg': a.msg, 'project': a.project, 'level': a.level})
