from httpx import AsyncClient
from opyoid import Injector

from src.mybootstrap_core_itskovichanton import ioc
from src.mybootstrap_core_itskovichanton.config import YamlConfigLoaderService, ConfigLoaderService, ConfigService
from src.mybootstrap_core_itskovichanton.ioc import BaseModule


class CoreModule(BaseModule):
    def configure(self) -> None:
        super().configure()

        self.bind(AsyncClient)
        self.bind(ConfigLoaderService, to_instance=YamlConfigLoaderService("config.yml", "dev"))


injector = Injector([CoreModule])
config_service = injector.inject(ConfigService)
ioc.settings = config_service.config.settings
ioc.profile = config_service.config.profile
