from typing import Protocol

from src.mybootstrap_ioc_itskovichanton.ioc import bean


class AbstractBean(Protocol):
    pass


@bean(no_polymorph=True)
class OtherBean(AbstractBean):

    def init(self):
        print("OtherBean Constructed")


@bean(no_polymorph=True, p1="qcb", p2="email.encoding", p4=("a.b.c.d", None, {"x": 1, "y": 2}))
class MyBean(AbstractBean):
    other_bean: OtherBean

    def init(self, **kwargs):
        print("MyBean Constructed")

    def info(self) -> str:
        return f"info() = {self.p4}"


class AbstractService:
    def do_smth(self):
        pass


@bean(profile="prod", appdata_env="APPDATA")
class ProdService(AbstractService):
    other_bean: OtherBean

    def init(self, **kwargs):
        print("ProdBean Constructed")

    def do_smth(self):
        print(f"I am ProdBean and i'm working! {self.appdata_env}")


@bean(profile="dev")
class DevService(AbstractService):
    other_bean: OtherBean

    def init(self, **kwargs):
        print("DevBean Constructed")

    def do_smth(self):
        print("I am DevBean and i'm working!")
