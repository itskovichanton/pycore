from typing import Protocol, Any

from src.mybootstrap_core_itskovichanton.ioc import bean


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
