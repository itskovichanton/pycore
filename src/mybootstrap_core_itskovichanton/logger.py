import functools
import logging
import os
import traceback
from datetime import datetime
from logging import Logger
from logging.handlers import TimedRotatingFileHandler
from typing import Protocol

from pythonjsonlogger import jsonlogger
from src.mybootstrap_core_itskovichanton.config import ConfigService
from src.mybootstrap_ioc_itskovichanton.ioc import bean


class LoggerService(Protocol):
    def get_file_logger(self, name: str, encoding: str = "utf-8") -> Logger:
        pass


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get('t'):
            now = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            log_record['t'] = now


logger_service: LoggerService


@bean
class LoggerServiceImpl(LoggerService):
    config_service: ConfigService

    def get_file_logger(self, name: str, encoding: str = "utf-8") -> Logger:
        r = logging.getLogger(name)
        if hasattr(r, "inited"):
            return r

        logger_settings_prefix = "loggers." + name
        settings = self.config_service.config.settings
        r.setLevel(settings.get(logger_settings_prefix + ".level", logging.INFO))
        log_handler = TimedRotatingFileHandler(
            encoding=encoding,
            filename=f"{os.path.join(self.config_service.dir('logs'), name)}-{self.config_service.app_name()}.txt",
            when=settings.get(logger_settings_prefix + ".when", "midnight"),
            backupCount=settings.get(logger_settings_prefix + ".backup_count", 10))
        formatter = CustomJsonFormatter("%(t)s %(msg)s")
        log_handler.setFormatter(formatter)
        r.addHandler(log_handler)

        r.inited = True
        return r


def log(_logger, _desc=None, _func=None):
    def log_decorator_info(func):
        @functools.wraps(func)
        def log_decorator_wrapper(self, *args, **kwargs):
            args_passed_in_function = [repr(a) for a in args]
            kwargs_passed_in_function = [f"{k}={v!r}" for k, v in kwargs.items()]
            formatted_arguments = ", ".join(args_passed_in_function + kwargs_passed_in_function)
            desc = _desc
            if callable(desc):
                desc = desc(args, kwargs)
            else:
                if not desc or len(desc) == 0:
                    desc = str(func)
                desc += f": args={formatted_arguments}"
            logger = _logger
            if not isinstance(logger, logging.Logger):
                logger = logging.getLogger(str(logger))
            try:
                err_info = func(self, *args, **kwargs)
                desc += f"; result={err_info!r}"
                logger.info(desc)
            except BaseException as e:
                err_info = "\n".join(traceback.format_exception(e))
                desc += f"; error: {err_info!r}"
                logger.error(desc)
                raise
            return err_info

        return log_decorator_wrapper

    if _func is None:
        return log_decorator_info
    else:
        return log_decorator_info(_func)
