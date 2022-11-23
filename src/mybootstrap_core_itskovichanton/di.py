from typing import List, Union, Type

from httpx import AsyncClient
from opyoid import Injector, AbstractModule

from src.mybootstrap_core_itskovichanton import ioc, alerts
from src.mybootstrap_core_itskovichanton.alerts import AlertService
from src.mybootstrap_core_itskovichanton.config import ConfigService
from src.mybootstrap_core_itskovichanton.ioc import BaseModule
from src.mybootstrap_core_itskovichanton.utils import append_benedict


class CoreModule(BaseModule):
    def configure(self) -> None:
        super().configure()
        self.bind(AsyncClient)


config_service: ConfigService


def init(modules: List[Union[AbstractModule, Type[AbstractModule]]] = None) -> Injector:
    injector = Injector(modules)
    global config_service
    config_service = injector.inject(ConfigService)
    append_benedict(ioc.context.properties, config_service.config.settings)
    alerts.alert_service = injector.inject(AlertService)
    return injector
