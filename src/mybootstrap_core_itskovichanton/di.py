from opyoid import Injector
from paprika import singleton
from src.mybootstrap_ioc_itskovichanton import di

from src.mybootstrap_core_itskovichanton import alerts, logger, tracer
from src.mybootstrap_core_itskovichanton.alerts import AlertService
from src.mybootstrap_core_itskovichanton.logger import LoggerService


@singleton
def injector() -> Injector:
    _injector = di.injector()
    alerts.alert_service = _injector.inject(AlertService)
    logger.logger_service = _injector.inject(LoggerService)
    return _injector
