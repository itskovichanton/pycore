from httpx import AsyncClient
from opyoid import Injector

from src.mybootstrap_core_itskovichanton import ioc
from src.mybootstrap_core_itskovichanton.config import ConfigService
from src.mybootstrap_core_itskovichanton.ioc import BaseModule
from src.mybootstrap_core_itskovichanton.utils import append_benedict


class CoreModule(BaseModule):
    def configure(self) -> None:
        super().configure()
        self.bind(AsyncClient)


injector = Injector([CoreModule])
config_service = injector.inject(ConfigService)
append_benedict(ioc.context.properties, config_service.config.settings)
