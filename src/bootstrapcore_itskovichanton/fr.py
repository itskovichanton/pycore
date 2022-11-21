from contextlib import suppress
from dataclasses import dataclass
from typing import Protocol

import httpx
from dacite import from_dict

from src.bootstrapcore_itskovichanton.config import ConfigService


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


class FRServiceImpl(FRService):

    def __init__(self, config_service: ConfigService):
        fr_settings = config_service.config.settings["fr"]
        self.config = from_dict(data_class=FRConfig, data=fr_settings)
        self.http_client = httpx.AsyncClient()

    async def send(self, a: Post):
        if self.config is None:
            return
        with suppress(BaseException):
            await self.http_client.post(self.config.url + "/postMsg",
                                        data={'msg': a.msg, 'project': a.project, 'level': a.level})
