import subprocess
from typing import Protocol

from src.mybootstrap_ioc_itskovichanton.ioc import bean
from src.mybootstrap_mvc_itskovichanton.exceptions import CoreException

from src.mybootstrap_core_itskovichanton.utils import is_windows


class ShellService(Protocol):
    def execute(self, *args, encoding: str = None):
        pass

    def popen(self, *args, encoding: str = None):
        pass


@bean(executor="sh.executor", encoding=("sh.encoding", "str", "utf-8"))
class ShellServiceImpl(ShellService):

    def popen(self, *args, encoding: str = None):
        if is_windows():
            args = ["cmd", "/c", self.executor] + list(args)
        if not encoding:
            encoding = self.encoding
        return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding=encoding)

    def execute(self, *args, encoding: str = None):
        output, error = self.popen(*args, encoding=encoding).communicate()
        if error:
            error = error.strip()
            if len(error) > 0:
                raise CoreException(message=error)
        if output:
            output = output.strip()
        return output
