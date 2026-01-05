import subprocess
from typing import Protocol

from src.mybootstrap_ioc_itskovichanton.config import ConfigService
from src.mybootstrap_ioc_itskovichanton.ioc import bean
from src.mybootstrap_mvc_itskovichanton.exceptions import CoreException

from src.mybootstrap_core_itskovichanton.logger import log
from src.mybootstrap_core_itskovichanton.utils import is_windows


class ShellService(Protocol):
    def execute(self, *args, encoding: str = None, cwd=None):
        ...

    def popen(self, *args, encoding: str = None, cwd=None):
        ...


@bean(print_commands=("sh.executor.print_commands", bool, True), executor="sh.executor",
      encoding=("sh.encoding", str, "utf-8"))
class ShellServiceImpl(ShellService):
    config_service: ConfigService

    def popen(self, *args, encoding: str = None, cwd=None):
        if is_windows():
            args = ["cmd", "/c", self.executor] + list(args)
        if not encoding:
            encoding = self.encoding
        args = [str(x) for x in args]
        if self.print_commands:
            print(" ".join(args))
        return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding=encoding, cwd=cwd)

    @log("shell")
    def execute(self, *args, encoding: str = None, cwd=None):
        output, error = self.popen(*args, encoding=encoding, cwd=cwd).communicate()
        if error:
            error = error.strip()
            if len(error) > 0:
                raise CoreException(message=error)
        if output:
            output = output.strip()
        return output
