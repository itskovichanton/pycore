from opyoid import Injector

from src.mybootstrap_core_itskovichanton import ioc
from src.mybootstrap_core_itskovichanton.app import Application
from src.mybootstrap_core_itskovichanton.di import CoreModule
from src.mybootstrap_core_itskovichanton.ioc import BaseModule
from tests.app import TestCoreApp


class TestCoreModule(BaseModule):
    def configure(self) -> None:
        super().configure()
        self.install(CoreModule)
        self.bind(Application, to_class=TestCoreApp)


# print(ioc.beans)
injector = Injector([TestCoreModule])
