import subprocess
from src.mybootstrap_core_itskovichanton.utils import is_windows
from src.mybootstrap_ioc_itskovichanton.ioc import bean
from src.mybootstrap_mvc_itskovichanton.exceptions import CoreException
from typing import Protocol


class ShellService(Protocol):
    def execute(self, *args, encoding: str = None, cwd=None):
        ...

    def popen(self, *args, encoding: str = None, cwd=None):
        ...


@bean(executor="sh.executor", encoding=("sh.encoding", str, "utf-8"))
class ShellServiceImpl(ShellService):

    def popen(self, *args, encoding: str = None, cwd=None):
        if is_windows():
            args = ["cmd", "/c", self.executor] + list(args)
        if not encoding:
            encoding = self.encoding
        return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding=encoding, cwd=cwd)

    def execute(self, *args, encoding: str = None, cwd=None):
        output, error = self.popen(*args, encoding=encoding, cwd=cwd).communicate()
        if error:
            error = error.strip()
            if len(error) > 0:
                raise CoreException(message=error)
        if output:
            output = output.strip()
        return output
