import os
import subprocess
import tempfile
from dataclasses import dataclass
from os.path import basename
from typing import Protocol

from src.mybootstrap_ioc_itskovichanton.config import ConfigService
from src.mybootstrap_ioc_itskovichanton.ioc import bean
from src.mybootstrap_mvc_itskovichanton.exceptions import CoreException

from src.mybootstrap_core_itskovichanton.logger import log
from src.mybootstrap_core_itskovichanton.ssh import SSHConfig, SSHClient
from src.mybootstrap_core_itskovichanton.utils import is_windows


class ShellService(Protocol):
    def execute(self, *args, encoding: str = None, cwd=None):
        ...

    def popen(self, *args, encoding: str = None, cwd=None):
        ...

    def execute_bash(self, script: str = None, cwd=None, ssh_config: SSHConfig = None, **kwargs):
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
    def execute(self, *args, encoding: str = None, cwd=None, suppress_error=None):
        output, error = self.popen(*args, encoding=encoding, cwd=cwd).communicate()
        print(f"error={error}")
        print(f"output={output}")
        if error:
            error = error.strip()
            if len(error) > 0 and not (suppress_error and suppress_error(error)):
                raise CoreException(message=error)
        if output:
            output = output.strip()
        return output

    def execute_bash(self, script: str = None, cwd=None, ssh_config: SSHConfig = None, **kwargs):

        script = script.strip()

        if ssh_config:
            with SSHClient(ssh_config, working_directory=ssh_config.cwd or cwd) as cl:
                r = cl.execute_bash_script(script_content=script)
                if not r["success"]:
                    raise CoreException(message=r["stderr"] or r["stdout"], exit_code=r["exit_code"])
                if ssh_config.download_file_args:
                    if not ssh_config.download_file_args.local_path:
                        ssh_config.download_file_args.local_path = os.path.join(self.config_service.dir("cmd"),
                                                                                basename(
                                                                                    ssh_config.download_file_args.remote_path))
                    ssh_config.download_file_args.success = cl.download_file(ssh_config.download_file_args.remote_path,
                                                                             ssh_config.download_file_args.local_path)
                return r["stdout"]

        global script_file
        try:
            # Создаем временный файл для скрипта
            script_file = tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False)
            script_file.write(script)
            script_file.close()
            return self.execute("bash", script_file.name, *[f"{k} {v}" for k, v in kwargs], cwd=cwd,
                                suppress_error=lambda err: err.startswith("cat: /tmp/"))
        finally:
            # Удаляем локальный временный файл
            os.unlink(script_file.name)
