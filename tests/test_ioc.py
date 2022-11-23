from typing import Protocol

from src.mybootstrap_core_itskovichanton.config import ConfigService
from src.mybootstrap_core_itskovichanton.ioc import bean


class AbstractBean(Protocol):
    pass


@bean(no_polymorph=True)
class OtherBean(AbstractBean):

    def post_construct(self):
        print("OtherBean Constructed")


@bean(no_polymorph=True)
class MyBean(AbstractBean):
    config_service: ConfigService
    other_bean: OtherBean
    url: str = None

    def post_construct(self):
        self.profile = self.config_service.config.profile
        print("MyBean Constructed")

    def info(self) -> str:
        return self.config_service.config.profile
