import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from paprika import threaded
from src.mybootstrap_ioc_itskovichanton.config import ConfigService
from src.mybootstrap_ioc_itskovichanton.ioc import bean

from src.mybootstrap_core_itskovichanton.alerts import alert_on_fail
from src.mybootstrap_core_itskovichanton.logger import LoggerService
from src.mybootstrap_core_itskovichanton.shell import ShellService
from src.mybootstrap_core_itskovichanton.utils import silent_catch, is_windows


@dataclass
class _Handler:
    trigger: str
    action: str
    args: Any
    enabled: bool = True


@dataclass
class _Config:
    service_name: str
    dependent_services: list[str] = None
    handlers: dict[str, _Handler] = None


@bean(cfg=("watchdog", _Config, None))
class Watchdog:
    config_service: ConfigService
    logger_service: LoggerService
    shell: ShellService

    def init(self, **kwargs):
        if not self.cfg:
            return
        if is_windows():
            return
        if not self.cfg.dependent_services:
            self.cfg.dependent_services = []
        self._init_handlers()

    @threaded
    def _init_handlers(self):
        for handler_name, handler in self.cfg.handlers.items():
            if not handler.enabled:
                continue
            if handler.trigger == "log-file-growth-stopped+healthcheck":
                self._create_watchdog_service(handler_name, handler)

    @alert_on_fail(supress=True)
    def _create_watchdog_service(self, handler_name: str, handler: _Handler):
        srv_name = self.get_systemctl_service_name(handler_name)
        script_file = self._write_script_restart_on_file_growth_stopped(handler_name, handler)
        if self.is_service_active(srv_name):
            return
        self._write_service(handler_name, script_file, srv_name)
        self._start_service(handler_name, srv_name)

    def _write_script_restart_on_file_growth_stopped(self, handler_name: str, handler: _Handler):
        srv_script_file = os.path.join(self.config_service.dir("watchdog"), f"{handler_name}.sh")
        with open(srv_script_file, 'w', encoding='utf-8') as f:
            f.write(self._compose_script_restart_on_file_growth_stopped(handler))
        return os.path.abspath(srv_script_file)

    def _compose_script_restart_on_file_growth_stopped(self, handler: _Handler):
        return f"""#!/bin/bash

### Description: {handler} ###

LOG_FILE="{self.logger_service.get_file_logger(handler.args['log']).handlers[0].baseFilename}"

reanimate() {{
\tif [ "$GOODNIGHT_TIME" = "yes" ]; then
\t\treturn
\tfi
\tsystemctl restart {self.cfg.service_name}.service
""" + "\n".join([f"\tsystemctl restart {dependent_service}.service" for dependent_service in
                 self.cfg.dependent_services]) + f"""
}}

current_size=$(stat -c %s $LOG_FILE)

while true
do
\tsleep {60 * handler.args.get('interval_min') or 10}
    
\t""" + self.get_ping_port_command(handler) + """
\tnew_size=$(stat -c %s $LOG_FILE)
    
\tif [ $new_size -eq $current_size ]; then
\t\techo "Размер файла не изменился. Перезапуск сервиса"
\t\treanimate
\t\tcurrent_size=$new_size
\tfi
done"""

    def _write_service(self, handler_name, script_file, srv_name):
        srv_file = f"/etc/systemd/system/{srv_name}"
        Path(f"/var/log/{srv_name}").mkdir(parents=True, exist_ok=True)
        with open(srv_file, 'w', encoding='utf-8') as f:
            f.write(self._compose_service_desc(handler_name, script_file, srv_name))
        print(srv_file)
        return srv_file

    def _compose_service_desc(self, handler_name, script_file, srv_name):
        return f"""[Unit]
Description={srv_name}
After=multi-user.target

[Service]
Type=simple
WorkingDirectory={os.path.dirname(script_file)}
ExecStart=bash {script_file}
Restart=always
RestartSec=3

StandardOutput=append:/var/log/{srv_name}/{handler_name}.log
StandardError=append:/var/log/{srv_name}/{handler_name}.err.log
"""

    def _start_service(self, handler_name, srv_name):
        silent_catch()(self.shell.execute("sudo", "systemctl", "daemon-reload"))
        silent_catch()(self.shell.execute("sudo", "systemctl", "start", srv_name))
        silent_catch()(self.shell.execute("sudo", "systemctl", "enable", srv_name))
        self.shell.execute("sudo", "systemctl", "status", srv_name)

    def get_ping_port_command(self, handler: _Handler):
        port = handler.args.get('port')
        if not port:
            return ""
        return f"""curl -m {handler.args.get('healthcheck_timeout') or 10} http://localhost:{port}/{handler.args.get('healthcheck_endpoint') or "healthcheck"} >/dev/null 2>&1
\tif [ $? -eq 28 ] || [ $? -eq 7 ]; then
\t\techo "Запрос curl на порт оборвался таймауту. Перезапуск сервиса"
\t\treanimate
\tfi
"""

    def is_service_active(self, service_name):
        command = f'systemctl status {service_name}'

        try:
            output = subprocess.check_output(command, shell=True).decode('utf-8')

            if "active (running)" in output:
                return True
            else:
                return False
        except:
            return False

    def get_systemctl_service_name(self, handler_name: str):
        srv_name = f"watchdog-{self.config_service.app_name()}-{handler_name}.service"
        srv_name = srv_name.replace("[", "-").replace("]", "-")
        return srv_name
