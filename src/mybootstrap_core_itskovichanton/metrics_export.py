from dataclasses import dataclass

from prometheus_client import start_http_server
from src.mybootstrap_ioc_itskovichanton.config import ConfigService
from src.mybootstrap_ioc_itskovichanton.ioc import bean

import time
from prometheus_client import Gauge
from src.mybootstrap_ioc_itskovichanton.config import ConfigService

from src.mybootstrap_core_itskovichanton.di import injector

from src.mybootstrap_core_itskovichanton.utils import singleton


@singleton
def get_gauge(metric_name, doc) -> Gauge:
    return Gauge(metric_name, doc, [])


def prometheus_metric(metric_name):
    def decorator(func):
        # @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            # Создаем метрику в Prometheus
            metric = get_gauge(metric_name, doc=f'execution time of {func.__name__} in milliseconds')
            metric.set(execution_time)

            return result

        return wrapper

    return decorator


@dataclass
class _Config:
    port: int = 1212
    enabled: bool = False
    frontend_url: str = "http://localhost:9090/graph"


@bean(config=("metrics.prometheus", _Config, _Config()))
class MetricsExporter:
    config_service: ConfigService

    def init(self, **kwargs):
        if self.config.enabled:
            start_http_server(self.config.port)

    @singleton
    def get_gauge_name(self, metric_name):
        metric_name = f"{self.config_service.app_name()}_{metric_name}"
        chars_to_replace = ['[', ']', '-', '.']
        for char in chars_to_replace:
            metric_name = metric_name.replace(char, '_')
        return metric_name

    def get_metrics_url(self, metric_name):
        return f"{self.config.frontend_url}?g0.expr={self.get_gauge_name(metric_name)}"