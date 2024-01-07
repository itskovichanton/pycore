from dataclasses import dataclass

from prometheus_client import start_http_server
from src.mybootstrap_ioc_itskovichanton.config import ConfigService
from src.mybootstrap_ioc_itskovichanton.ioc import bean


@dataclass
class _Config:
    port: int = 1212
    enabled: bool = False


@bean(config=("metrics.prometheus", _Config, _Config()))
class MetricsExporter:
    config_service: ConfigService

    def init(self, **kwargs):
        if self.config.enabled:
            start_http_server(self.config.port)
