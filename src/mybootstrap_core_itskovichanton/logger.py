import codecs
import functools
import glob
import logging
import logging.handlers
import os
import time
import traceback
import zipfile
from datetime import datetime
from logging import Logger
from pathlib import Path
from typing import Protocol

import patoolib
from paprika import threaded
from pythonjsonlogger import jsonlogger
from src.mybootstrap_ioc_itskovichanton.config import ConfigService
from src.mybootstrap_ioc_itskovichanton.ioc import bean

from src.mybootstrap_core_itskovichanton import alerts
from src.mybootstrap_core_itskovichanton.alerts import Alert
from src.mybootstrap_core_itskovichanton.utils import trim_string, to_dict_deep, unescape_str


class LoggerService(Protocol):
    def get_file_logger(self, name: str, encoding: str = "utf-8", formatter=None) -> Logger:
        ...


class SimpleJsonFormatter(jsonlogger.JsonFormatter):

    def __init__(self, *args, trim_values_len=2000, **kwargs):
        super().__init__(*args, **kwargs)
        self.trim_values_len = trim_values_len

    def add_fields(self, log_record, record, message_dict):
        super(SimpleJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get('t'):
            log_record['t'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        self.preprocess_log_record(log_record)
        log_record.pop("msg", None)

        if self.trim_values_len > 0:
            trimmed_e = to_dict_deep(log_record,
                                     value_mapper=lambda _, v: trim_string(str(v), limit=self.trim_values_len))
            log_record.clear()
            log_record.update(trimmed_e)

    def jsonify_log_record(self, log_record):
        r = super().jsonify_log_record(log_record)
        return unescape_str(r)

    def preprocess_log_record(self, log_record):
        ...


logger_service: LoggerService


class LogCompressor(Protocol):

    def compress_entry(self, log_type: str, e):
        ...

    def compress(self, log_type: str, file: str) -> str:
        ...


class TimedCompressedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):

    def __init__(self, filename, when='h', interval=1, backupCount=0, encoding=None, delay=False, utc=False,
                 atTime=None, errors=None, log_compressor: LogCompressor = None, name=None, archive_type="rar"):
        super().__init__(filename, when, interval, backupCount, encoding, delay, utc, atTime, errors)
        self.log_compressor = log_compressor
        self.name = name
        self.archive_type = archive_type

    def doRollover(self):

        if self.stream:
            self.stream.close()

        # get the time that this sequence started at and make it a TimeTuple
        t = self.rolloverAt - self.interval
        time_tuple = time.localtime(t)
        dfn = self.baseFilename + "." + time.strftime(self.suffix, time_tuple)
        if os.path.exists(dfn):
            os.remove(dfn)
        os.rename(self.baseFilename, dfn)
        if self.backupCount > 0:
            # find the oldest log file and delete it
            # s = glob.glob(self.baseFilename + ".20*")
            s = glob.glob(f"{Path(self.baseFilename).parent.absolute()}/*.{datetime.now().year}*")
            if len(s) > self.backupCount:
                s.sort()
                os.remove(s[0])
        # print "%s -> %s" % (self.baseFilename, dfn)
        # if self.log_compressor:
        #     dfn = self.log_compressor.compress(log_type=self.name, file=dfn)
        if self.encoding:
            self.stream = codecs.open(self.baseFilename, 'w', self.encoding)
        else:
            self.stream = open(self.baseFilename, 'w')

        self.rolloverAt = self.rolloverAt + self.interval

        if self.archive_type == "rar":
            if os.path.exists(dfn + ".rar"):
                os.remove(dfn + ".rar")
            patoolib.create_archive(dfn + ".rar", [dfn], program='rar', verbosity=-1)
        else:
            if os.path.exists(dfn + ".zip"):
                os.remove(dfn + ".zip")
            file = zipfile.ZipFile(dfn + ".zip", "w")
            file.write(dfn, os.path.basename(dfn), zipfile.ZIP_DEFLATED)
            file.close()

        os.remove(dfn)


@bean
class LoggerServiceImpl(LoggerService):
    config_service: ConfigService
    log_compressor: LogCompressor = None

    def get_file_logger(self, name: str, encoding: str = "utf-8",
                        formatter=None) -> Logger:
        r = logging.getLogger(name)
        if hasattr(r, "inited"):
            return r

        logger_settings_prefix = "loggers." + name
        settings = self.config_service.config.settings
        r.setLevel(settings.get(logger_settings_prefix + ".level", logging.INFO))
        log_handler = TimedCompressedRotatingFileHandler(
            archive_type=settings.get(logger_settings_prefix + ".archive_type", "zip"),
            log_compressor=self.log_compressor,
            name=name,
            encoding=encoding,
            filename=f"{os.path.join(self.config_service.dir('logs'), name)}-{self.config_service.app_name()}.txt",
            when=settings.get(logger_settings_prefix + ".when", "midnight"),
            backupCount=settings.get(logger_settings_prefix + ".backup_count", 365))

        if not formatter:
            formatter = SimpleJsonFormatter("%(t)s %(msg)s")
        log_handler.setFormatter(formatter)

        r.addHandler(log_handler)

        r.inited = True

        return r


def lg(logger, desc=None, action=None, alert=False):
    s = ": ".join([action, desc])
    if not isinstance(logger, logging.Logger):
        logger = logging.getLogger(str(logger))
    logger.info(s)
    print(s)
    if alert:
        alerts.alert_service.send(Alert(subject=action, message=desc))


@threaded
def async_log(logger, entry, tp):
    if tp == "error":
        logger.error(entry)
    else:
        logger.info(entry)


def log(_logger, _desc=None, _func=None, _action=None, _alert=False, _ignore_if_success=False, _preprocess_result=None):
    def log_decorator_info(func):
        @functools.wraps(func)
        def log_decorator_wrapper(self, *args, **kwargs):
            args_passed_in_function = [repr(a) for a in args]
            kwargs_passed_in_function = [{k: v for k, v in kwargs.items()}]
            # formatted_arguments = ", ".join(args_passed_in_function + kwargs_passed_in_function)
            e = {}
            e["args"] = args_passed_in_function + kwargs_passed_in_function
            desc = _desc
            if callable(desc):
                desc = desc(args, kwargs)
            else:
                if not desc or len(desc) == 0:
                    desc = str(func)
            if type(desc) != dict:
                desc = {"desc": desc}
            e["args"] += desc

            if _action:
                e["action"] = _action
                desc = f"{_action}: {desc}"
            # desc += f": args={formatted_arguments}"
            logger = _logger
            if not isinstance(logger, logging.Logger):
                logger = logger_service.get_file_logger(str(logger))
            try:
                result = func(self, *args, **kwargs)
                # if _preprocess_result and callable(_preprocess_result):
                #     result=_preprocess_result(copy(result))
                # desc += f"; result={result!r}"
                e["result"] = result
                if _alert:
                    alerts.alert_service.send(Alert(subject=_action, message=desc))
                if _ignore_if_success:
                    return

                async_log(logger, e, "info")
                # print(desc)

            except BaseException as ex:
                result = "\n".join(traceback.format_exception(ex))
                desc += {"error": f"{result!r}"}
                e["result"] = result
                async_log(logger, e, "error")
                print(desc)
                if _alert:
                    alerts.alert_service.handle(ex)
                raise ex
            return result

        return log_decorator_wrapper

    if _func is None:
        return log_decorator_info
    else:
        return log_decorator_info(_func)
