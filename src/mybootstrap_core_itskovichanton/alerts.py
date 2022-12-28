import functools
import logging
import traceback
from dataclasses import dataclass
from typing import Protocol, Callable

from src.mybootstrap_ioc_itskovichanton.ioc import bean
from src.mybootstrap_ioc_itskovichanton.utils import default_dataclass_field

from src.mybootstrap_core_itskovichanton.config import ConfigService
from src.mybootstrap_core_itskovichanton.email import EmailService, Params
from src.mybootstrap_core_itskovichanton.fr import FRService, Post
from src.mybootstrap_core_itskovichanton.utils import trim_string


@dataclass
class Alert:
    message: str = None
    subject: str = None
    byEmail: bool = True
    byFR: bool = True
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


alert_service: AlertService


@bean(emails="alerts.emails", from_email="email.from")
class AlertServiceImpl(AlertService):
    config_service: ConfigService
    fr_service: FRService
    email_service: EmailService
    _interceptors: list[ExceptionInterceptor] = default_dataclass_field([])

    def get_interceptors(self) -> list[ExceptionInterceptor]:
        return self._interceptors

    def send(self, a: Alert):
        if not a.send:
            return

        if not a.subject:
            a.subject = "NO TOPIC"

        a.subject = f"{self.config_service.app_name()} - [{a.subject}]"

        if a.byFR:
            self.send_by_fr(a)

        if a.byEmail:
            pass
            # self.send_by_email(a)

    def send_by_fr(self, a):
        self.fr_service.send(Post(project=a.subject, level=a.level, msg=trim_string(a.message, 4000)))

    def send_by_email(self, a):
        self.email_service.send(
            Params(subject=a.subject, toEmail=self.emails, senderEmail=self.from_email, content_plain=a.message))

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
        for interceptor in self._interceptors:
            if interceptor:
                e = interceptor(e)
                if e is None:
                    break
        return e


def alert_on_fail(method, alert: Alert = Alert()):
    @functools.wraps(method)
    def _impl(*method_args, **method_kwargs):
        try:
            return method(*method_args, **method_kwargs)
        except BaseException as e:
            alert_service.handle(e, alert)

    return _impl
