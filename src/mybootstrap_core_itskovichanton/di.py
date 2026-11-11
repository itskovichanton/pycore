"""
Общий injector ядра: поднимает IoC pyioc и проставляет глобальные
``alerts.alert_service`` и ``logger.logger_service``.
"""
from opyoid import Injector
from paprika import singleton
from src.mybootstrap_ioc_itskovichanton import di

from src.mybootstrap_core_itskovichanton import alerts, logger
from src.mybootstrap_core_itskovichanton.alerts import AlertService
from src.mybootstrap_core_itskovichanton.logger import LoggerService


@singleton
def injector() -> Injector:
    """Синглтон-контейнер приложения; первый вызов инициализирует алерты и логгер."""
    _injector = di.injector()
    alerts.alert_service = _injector.inject(AlertService)
    logger.logger_service = _injector.inject(LoggerService)
    return _injector
