import logging
import sys
import threading
import traceback
from dataclasses import dataclass
from typing import Protocol, Callable, Any

from retrying import retry

from src.mybootstrap_core_itskovichanton.utils import is_network_connection_failed, with_empty_method
from src.mybootstrap_ioc_itskovichanton.config import ConfigService
from src.mybootstrap_ioc_itskovichanton.ioc import bean
from src.mybootstrap_ioc_itskovichanton.utils import default_dataclass_field, omittable_parentheses
from src.mybootstrap_mvc_itskovichanton.exceptions import CoreException, \
    ERR_REASON_SERVER_RESPONDED_WITH_ERROR_NOT_FOUND


@with_empty_method
@dataclass
class Alert:
    message: Any = None
    subject: str = None
    level: int = 1
    send: bool = True


ExceptionInterceptor = Callable[[BaseException], BaseException]


class AlertService(Protocol):

    def get_interceptors(self) -> list[ExceptionInterceptor]:
        """Get interceptors"""

    def send(self, a: Alert):
        """Send alert"""

    def handle(self, e: BaseException, alert: Alert = Alert()):
        """Send alert about exception"""

    def register_handler(self, action):
        ...


alert_service: AlertService


@bean
class AlertServiceImpl(AlertService):
    config_service: ConfigService
    _interceptors: list[ExceptionInterceptor] = default_dataclass_field([])
    handlers: list[callable] = default_dataclass_field([])

    def init(self, **kwargs):
        sys.excepthook = self._handle_uncaught_from_main_thread
        threading.excepthook = self._handle_uncaught_from_async_threads

    def _handle_uncaught_from_async_threads(self, args):
        self.handle(CoreException(
            message=f"Exception from thread {args.thread.name}\n" +
                    ''.join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))),
        )

    def _handle_uncaught_from_main_thread(self, type, value, tb):
        self.handle(CoreException(
            message="Exception from main thread\n" + ''.join(traceback.format_exception(type, value, tb))))

    def get_interceptors(self) -> list[ExceptionInterceptor]:
        return self._interceptors

    def register_handler(self, action):
        self.handlers.append(action)

    def send(self, a: Alert):
        if (not a.send) or a.empty():
            return

        if not a.subject:
            a.subject = "NO TOPIC"

        a.subject = f"{self.config_service.app_name()} - [{a.subject}]"
        for handler in self.handlers:
            handler(a)

    def handle(self, e: BaseException, alert: Alert = Alert()):
        if not alert:
            return

        e = self._preprocess(e)
        if not e:
            return

        logging.exception(e)
        alert.message = "\n".join(traceback.format_exception(e))
        alert.subject = "Exception"
        self.send(alert)

    def _preprocess(self, e: BaseException) -> BaseException:
        if (isinstance(e, CoreException) and
                (getattr(e, "suppress_report", None) or e.reason == ERR_REASON_SERVER_RESPONDED_WITH_ERROR_NOT_FOUND)):
            return

        for interceptor in self._interceptors:
            if interceptor:
                e = interceptor(e)
                if e is None:
                    break
        return e


@omittable_parentheses(allow_partial=True)
def alert_on_fail(alert: Alert | Callable[[Exception], Alert] = Alert(),
                  supress: bool | Callable[[Exception], Any] = False):
    def wrapper(func):
        def inner(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except BaseException as e:
                _alert = alert
                if callable(_alert):
                    _alert = _alert(e)
                alert_service.handle(e, _alert)
                _supress = supress
                if callable(_supress):
                    _supress = _supress(e)
                if not _supress:
                    raise e

        return inner

    return wrapper


def retry_and_alert(func, sleep_ms=10000, retry_on=is_network_connection_failed, alert: Alert = None):
    @retry(wait_fixed=sleep_ms, retry_on_exception=retry_on)
    @alert_on_fail(alert=alert)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper
