import logging
import os
from datetime import datetime
from logging import Logger
from logging.handlers import TimedRotatingFileHandler
from typing import Protocol

from pythonjsonlogger import jsonlogger
from src.mybootstrap_core_itskovichanton.config import ConfigService
from src.mybootstrap_ioc_itskovichanton.ioc import bean


class LoggerService(Protocol):
    def get_file_logger(self, name: str) -> Logger:
        pass


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get('t'):
            now = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            log_record['t'] = now


@bean
class LoggerServiceImpl(LoggerService):
    config_service: ConfigService

    def get_file_logger(self, name: str) -> Logger:
        r = logging.getLogger(name)
        if hasattr(r, "inited"):
            return r

        logger_settings_prefix = "loggers." + name
        settings = self.config_service.config.settings
        r.setLevel(settings.get(logger_settings_prefix + ".level", logging.INFO))
        log_handler = TimedRotatingFileHandler(
            filename=f"{os.path.join(self.config_service.dir('logs'), name)}-{self.config_service.app_name()}.txt",
            when=settings.get(logger_settings_prefix + ".when", "midnight"),
            backupCount=settings.get(logger_settings_prefix + ".backup_count", 10))
        formatter = CustomJsonFormatter("%(t)s %(msg)s")
        log_handler.setFormatter(formatter)
        r.addHandler(log_handler)

        r.inited = True
        return r
