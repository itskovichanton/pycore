from opyoid import Module

from app import Application
from config import YamlConfigLoaderService, ConfigLoaderService, ConfigService, ConfigServiceImpl
from test_app import TestCoreApplication


class CoreModule(Module):
    def configure(self) -> None:
        self.bind(ConfigLoaderService, to_instance=YamlConfigLoaderService("config.yml", "dev"))
        self.bind(ConfigService, to_class=ConfigServiceImpl)
        self.bind(Application, to_class=TestCoreApplication)
