from opyoid import Module, Injector

from src.mybootstrap_core_itskovichanton.app import Application
from src.mybootstrap_core_itskovichanton.di import CoreModule
from tests.app import TestCoreApp


class TestCoreModule(Module):
    def configure(self) -> None:
        self.install(CoreModule)
        self.bind(Application, to_class=TestCoreApp)


injector = Injector([TestCoreModule])
