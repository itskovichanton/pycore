import codecs
import functools
import glob
import logging
import logging.handlers
import os
import threading
import time
import traceback
import uuid
import zipfile
from collections import deque, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from logging import Logger
from pathlib import Path
from typing import Protocol

import requests
# from pygelf import GelfUdpHandler
from pythonjsonlogger import jsonlogger
from requests import Session
from src.mybootstrap_ioc_itskovichanton import ioc
from src.mybootstrap_ioc_itskovichanton.config import ConfigService
from src.mybootstrap_ioc_itskovichanton.ioc import bean

from src.mybootstrap_core_itskovichanton import alerts
from src.mybootstrap_core_itskovichanton.alerts import Alert
from src.mybootstrap_core_itskovichanton.utils import trim_string, to_dict_deep, unescape_str, singleton, generate_uid, \
    UrlCheckResult, check_url_availability_by_url


@dataclass
class RequestStats:
    times: deque = field(default_factory=lambda: deque(maxlen=200))
    connection_success_count: int = 0
    connection_fail_count: int = 0
    response_statuses: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    last_err: str = None

    @property
    def avg_time(self):
        return sum(self.times) / len(self.times) if self.times else 0.0

    @property
    def max_time(self):
        return max(self.times) if self.times else 0.0

    def summary(self):
        return {
            "connection_success_count": self.connection_success_count,
            "connection_fail_count": self.connection_fail_count,
            "response_statuses": self.response_statuses,
            "last_err": self.last_err,
            "avg_time": self.avg_time,
            "max_time": self.max_time,
        }


class LoggerService(Protocol):

    def get_session_stats(self):
        ...

    def get_simple_file_logger(self, name) -> Logger:
        ...

    def get_graylog_logger(self, name: str) -> Logger:
        ...

    def get_logged_session(self, logger_name="outgoing-requests", url=None, route=None) -> Session:
        ...

    def get_file_logger(self, name: str, encoding: str = "utf-8",
                        formatter=None, max_line_len: int = 3000) -> Logger:
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


def _adapt_body(body):
    if body is None:
        return None

    if isinstance(body, bytes):
        return f"binary[{len(body)}]"

    text = str(body)
    if len(text) > 1000:
        return text[:1000] + "...(truncated)"
    return text


@dataclass
class SessionStats:
    stats: dict[str, RequestStats] = None
    availability: UrlCheckResult = None


@singleton(ttl=5 * 60)
def _check_url_availability(url):
    return check_url_availability_by_url(url)


class SessionWithStats(requests.Session):

    def __init__(self, name, logger=None, url=None, route=None):
        super().__init__()
        self.name = name
        self._stats = defaultdict(RequestStats)
        self._lock = threading.Lock()
        self._logger = logger or logging.getLogger(name)
        self._url = url
        self._route = route

    @property
    def stats(self) -> SessionStats:
        r = SessionStats(stats=self._stats)
        if self._url:
            r.availability = _check_url_availability(self._url)
        return r

    def request(self, method, url, *args, **kwargs):

        start = time.perf_counter()
        exc = None
        response = None

        # Запоминаем тело запроса
        req_body = kwargs.get("data") or kwargs.get("json") or None
        req_headers = kwargs.get("headers")

        if not req_headers:
            req_headers = {}

        if self.name:
            req_headers["User-Agent"] = self.name
        req_headers["X-Request-ID"] = generate_uid()

        try:
            response = super().request(method, url, *args, **kwargs)
            return response
        except Exception as e:
            exc = e
            raise
        finally:
            elapsed = time.perf_counter() - start
            if self._route:
                if callable(self._route):
                    route = self._route(url.split("?")[0])
                else:
                    route = self._route
            else:
                route = url.split("?")[0]

            # Обновляем статистику
            with self._lock:
                st = self._stats[route]
                st.times.append(elapsed)
                if exc is None:
                    st.connection_success_count += 1
                else:
                    st.connection_fail_count += 1
                    st.last_err = str(exc)
                if response:
                    st.response_statuses[str(response.status_code)] += 1

            # Логирование
            extra = {
                "req": {
                    "method": method,
                    "url": url,
                    "headers": dict(req_headers) if req_headers else None,
                    "body": _adapt_body(req_body),
                },
                "res": {
                    "code": response.status_code if response else None,
                    "reason": response.reason if response else None,
                    "url": response.url if response else None,
                    "headers": dict(response.headers) if response else None,
                    "body": _adapt_body(response.content if response else None),
                },
                "err": str(exc) if exc else None,
                "elapsed": elapsed,
            }

            self._logger.info(extra)


@bean
class LoggerServiceImpl(LoggerService):
    config_service: ConfigService
    log_compressor: LogCompressor = None

    def init(self, **kwargs):
        self._sessions: dict[str, SessionWithStats] = defaultdict(SessionWithStats)

    def get_session_stats(self):
        return {name: stats.stats for name, stats in self._sessions.items()}

    def get_simple_file_logger(self, name) -> Logger:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)  # Уровень логирования

        # Создание обработчика, который будет записывать лог-файлы
        file_handler = logging.FileHandler(
            f"{os.path.join(self.config_service.dir('logs'), name)}-{self.config_service.app_name()}.txt",
        )
        file_handler.setLevel(logging.DEBUG)

        # Создание форматтера и добавление его в обработчик
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        # Добавление обработчика в логгер
        logger.addHandler(file_handler)
        return logger

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
        # graylog_handler = GelfUdpHandler(host='localhost', port=12201)
        # r.addHandler(graylog_handler)
        r.addFilter(ContextFilter())
        r.inited = True
        return r

    @singleton
    def get_logged_session(self, logger_name="outgoing-requests", url=None, route=None) -> Session:
        logger = self.get_file_logger(logger_name)
        r = SessionWithStats(f"{self.config_service.app_name()}:{logger_name}", logger, url, route)
        self._sessions[logger_name] = r
        return r

    def get_file_logger(self, name: str, encoding: str = "utf-8",
                        formatter=None, max_line_len: int = 3000) -> Logger:
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
            formatter = SimpleJsonFormatter("%(t)s %(msg)s", trim_values_len=max_line_len)
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
    # if alert:
    #     alerts.alert_service.send(Alert(subject=action, message=desc))


def async_log(logger, entry, tp):
    if tp == "error":
        logger.error(entry)
    else:
        logger.info(entry)


def log(_logger, _fields: list = None, _desc=None, _func=None, _action=None, _alert_on_fail: bool = False,
        _alert_on_success: bool = False, _suppress_fail: bool = False, _include_elapsed_time: bool = True,
        with_extra: bool = False):
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
                if with_extra:
                    kwargs["__logextra__"] = {}
                result = func(self, *args, **kwargs)
                e["extra"] = kwargs.get("__logextra__")
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
