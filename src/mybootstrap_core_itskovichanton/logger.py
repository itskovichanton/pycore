import codecs
import functools
import glob
import logging
import logging.handlers
import os
import time
import traceback
import uuid
import zipfile
from datetime import datetime
from logging import Logger
from pathlib import Path
from typing import Protocol

import graypy
import requests
from paprika import threaded
from pygelf import GelfUdpHandler
from pythonjsonlogger import jsonlogger
from requests import Session
from src.mybootstrap_ioc_itskovichanton import ioc
from src.mybootstrap_ioc_itskovichanton.config import ConfigService
from src.mybootstrap_ioc_itskovichanton.ioc import bean

from src.mybootstrap_core_itskovichanton import alerts
from src.mybootstrap_core_itskovichanton.alerts import Alert
from src.mybootstrap_core_itskovichanton.utils import trim_string, to_dict_deep, unescape_str


class LoggerService(Protocol):

    def get_graylog_logger(self, name: str) -> Logger:
        ...

    def get_logged_session(self, logger_name="outgoing-requests") -> Session:
        ...

    def get_file_logger(self, name: str, encoding: str = "utf-8", formatter=None) -> Logger:
        ...


class SimpleJsonFormatter(jsonlogger.JsonFormatter):

    def __init__(self, *args, trim_values_len=3000, **kwargs):
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
                                     value_mapper=lambda _, v: trim_string(v, limit=self.trim_values_len)
                                     if type(v) == str else v)
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

    def __init__(self, filename, when='midnight', interval=1, backup_count=0, encoding=None, delay=False, utc=False,
                 at_time=None, errors=None, log_compressor: LogCompressor = None, name=None, archive_type="rar"):
        super().__init__(filename, when, interval, backup_count, encoding, delay, utc, at_time, errors)
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

        self.rolloverAt += self.interval

        if self.archive_type == "rar":
            if os.path.exists(dfn + ".rar"):
                os.remove(dfn + ".rar")
            import patoolib
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

    def get_graylog_logger(self, name: str) -> Logger:
        r = logging.getLogger(name)
        if hasattr(r, "inited"):
            return r

        class ContextFilter(logging.Filter):
            def filter(self, record):
                record.request_id = str(uuid.uuid4())
                return True

        logger_settings_prefix = "loggers." + name
        props = ioc.context.properties
        r.setLevel(props.get(logger_settings_prefix + ".level", logging.INFO))
        # graylog_handler =  graypy.GELFTCPHandler('0.0.0.0', 12201)
        graylog_handler = GelfUdpHandler(host='localhost', port=12201)
        r.addHandler(graylog_handler)
        r.addFilter(ContextFilter())
        r.inited = True
        return r

    def get_logged_session(self, logger_name="outgoing-requests") -> Session:
        logger = self.get_file_logger(logger_name)

        def _log_roundtrip(response, *args, **kwargs):
            extra = {
                'req': {
                    'method': response.request.method,
                    'url': response.request.url,
                    'headers': response.request.headers,
                    'body': response.request.body,
                },
                'res': {
                    'code': response.status_code,
                    'reason': response.reason,
                    'url': response.url,
                    'headers': response.headers,
                    'body': response.text
                },
            }
            logger.info('Outgoing', extra=extra)

        session = requests.Session()
        session.hooks['response'].append(_log_roundtrip)
        return session

    def get_file_logger(self, name: str, encoding: str = "utf-8",
                        formatter=None) -> Logger:
        r = logging.getLogger(name)
        if hasattr(r, "inited"):
            return r

        logger_settings_prefix = "loggers." + name
        props = ioc.context.properties
        r.setLevel(props.get(logger_settings_prefix + ".level", logging.INFO))
        log_handler = TimedCompressedRotatingFileHandler(
            archive_type=props.get(logger_settings_prefix + ".archive_type", "zip"),
            log_compressor=self.log_compressor,
            name=name,
            interval=1440 - (5 * 60),
            encoding=encoding,
            filename=f"{os.path.join(self.config_service.dir('logs'), name)}-{self.config_service.app_name()}.txt",
            when=props.get(logger_settings_prefix + ".when", "midnight"),
            backup_count=props.get(logger_settings_prefix + ".backup_count", 365))

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


def log(_logger, _fields: list = None, _desc=None, _func=None, _action=None, _alert_on_fail: bool = False,
        _alert_on_success: bool = False, _suppress_fail: bool = False, _include_elapsed_time: bool = True):
    def log_decorator_info(func):
        @functools.wraps(func)
        def log_decorator_wrapper(self, *args, **kwargs):
            args_passed_in_function = [repr(a) for a in args]
            fields = _fields
            kwargs_passed_in_function = {k: v for k, v in kwargs.items() if (fields is None) or (k in fields)}
            e = {"args": args_passed_in_function, "kwargs": kwargs_passed_in_function}

            desc = _desc
            if callable(desc):
                desc = desc(args, kwargs)
            if len(desc or "") > 0:
                e["desc"] = desc

            if _action:
                e["action"] = _action

            logger = _logger
            if not isinstance(logger, logging.Logger):
                logger = logger_service.get_file_logger(str(logger))

            result = None
            time_before = int(round(time.time() * 1000))
            try:
                result = func(self, *args, **kwargs)
                if _include_elapsed_time:
                    e["elapsed"] = int(round(time.time() * 1000) - time_before)
                e["result"] = result
                if _alert_on_success:
                    print(e)
                    alerts.alert_service.send(Alert(subject=_action, message=e))

                async_log(logger, e, "info")

            except BaseException as ex:
                if _include_elapsed_time:
                    e["elapsed"] = int(round(time.time() * 1000) - time_before)
                e["error"] = ";".join([s.replace("\n", ";") for s in traceback.format_exception(ex)])
                async_log(logger, e, "error")
                if _alert_on_fail:
                    alerts.alert_service.handle(ex)
                if not _suppress_fail:
                    raise ex

            return result

        return log_decorator_wrapper

    if _func is None:
        return log_decorator_info
    else:
        return log_decorator_info(_func)


def field(l: dict, field, value):
    l[field] = value


def action(l: dict, action):
    field(l, "action", action)


def args(l: dict, args):
    field(l, "args", args)


def subject(l: dict, subject):
    field(l, "subject", subject)


def result(l: dict, result):
    field(l, "result", result)


def ignore(l):
    field(l, "ignored", True)


def log_dict(l: dict, lg: Logger):
    if not l.get("ignored"):
        if l.get("err"):
            lg.error(l)
        else:
            lg.info(l)


def err(l: dict, e):
    field(l, "err", traceback.format_exception(e))
