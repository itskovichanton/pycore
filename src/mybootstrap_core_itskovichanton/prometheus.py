import time
from prometheus_client import Gauge
from src.mybootstrap_ioc_itskovichanton.config import ConfigService

from src.mybootstrap_core_itskovichanton.di import injector

from src.mybootstrap_core_itskovichanton.utils import singleton

app_name = injector().inject(ConfigService).app_name()


@singleton
def _get_gauge(metric_name, doc) -> Gauge:
    chars_to_replace = ['[', ']', '-', '.']
    metric_name = f"{app_name}_{metric_name}"
    for char in chars_to_replace:
        metric_name = metric_name.replace(char, '_')
    return Gauge(metric_name, doc, [])


def prometheus_metric(metric_name):
    def decorator(func):
        # @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            # Создаем метрику в Prometheus
            metric = _get_gauge(metric_name, doc=f'execution time of {func.__name__} in milliseconds')
            metric.set(execution_time)

            return result

        return wrapper

    return decorator
