from src.mybootstrap_core_itskovichanton import di
from src.mybootstrap_core_itskovichanton.di import CoreModule
from src.mybootstrap_core_itskovichanton.ioc import BaseModule
from tests.app import TestCoreApp


class TestCoreModule(BaseModule):
    def configure(self) -> None:
        super().configure()
        TestCoreApp  # just for import modules with beans
        self.install(CoreModule)


injector = di.init([TestCoreModule])
