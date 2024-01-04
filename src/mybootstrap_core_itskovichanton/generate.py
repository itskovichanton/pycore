from src.mybootstrap_ioc_itskovichanton.config import ConfigService
from src.mybootstrap_ioc_itskovichanton.ioc import bean


@bean
class CodeGenerator:
    config_service: ConfigService

    def generate(self):
        ...
