from src.mybootstrap_ioc_itskovichanton.ioc import BaseModule

from src.mybootstrap_core_itskovichanton import di
from src.mybootstrap_core_itskovichanton.di import CoreModule


class TestCoreModule(BaseModule):
    def configure(self) -> None:
        super().configure()
        self.install(CoreModule)


injector = di.init([TestCoreModule])
