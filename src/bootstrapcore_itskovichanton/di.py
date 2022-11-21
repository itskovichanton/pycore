from opyoid import Module, Injector

from src.bootstrapcore_itskovichanton.alerts import AlertService, AlertServiceImpl
from src.bootstrapcore_itskovichanton.config import YamlConfigLoaderService, ConfigLoaderService, ConfigService, ConfigServiceImpl
from src.bootstrapcore_itskovichanton.email_service import EmailServiceImpl, EmailService
from src.bootstrapcore_itskovichanton.fr import FRService, FRServiceImpl


class CoreModule(Module):
    def configure(self) -> None:
        self.bind(ConfigLoaderService, to_instance=YamlConfigLoaderService("config.yml", "dev"))
        self.bind(ConfigService, to_class=ConfigServiceImpl)
        self.bind(FRService, to_class=FRServiceImpl)
        self.bind(EmailService, to_class=EmailServiceImpl)
        self.bind(AlertService, to_class=AlertServiceImpl)
        # self.bind(Application, to_class=TestCoreApplication)
        self.bind(Injector, to_instance=Injector([self]))


injector = Injector([CoreModule])
