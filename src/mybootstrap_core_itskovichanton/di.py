from opyoid import Injector

from src.mybootstrap_core_itskovichanton.config import YamlConfigLoaderService, ConfigLoaderService
from src.mybootstrap_core_itskovichanton.ioc import BaseModule


class CoreModule(BaseModule):
    def configure(self) -> None:
        super().configure()

        self.bind(ConfigLoaderService, to_instance=YamlConfigLoaderService("config.yml", "dev"))


injector = Injector([CoreModule])
