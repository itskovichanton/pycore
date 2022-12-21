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

    async def send(self, a: Alert):
        """Send alert"""

    async def handle(self, e: BaseException, alert: Alert = Alert()):
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

    async def send(self, a: Alert):
        if not a.send:
            return

        if not a.subject:
            a.subject = "NO TOPIC"

        a.subject = f"{self.config_service.app_name()} - [{a.subject}]"

        if a.byFR:
            await self.send_by_fr(a)

        if a.byEmail:
            pass
            # self.send_by_email(a)

    async def send_by_fr(self, a):
        await self.fr_service.send(Post(project=a.subject, level=a.level, msg=trim_string(a.message, 4000)))

    def send_by_email(self, a):
        self.email_service.send(
            Params(subject=a.subject, toEmail=self.emails, senderEmail=self.from_email, content_plain=a.message))

    async def handle(self, e: BaseException, alert: Alert = Alert()):
        e = self._preprocess(e)
        if not e:
            return

        logging.exception(e)
        alert.message = "\n".join(traceback.format_exception(e))
        alert.subject = "Exception"
        await self.send(alert)

    def _preprocess(self, e: BaseException) -> BaseException:
        for interceptor in self._interceptors:
            if interceptor:
                e = interceptor(e)
                if e is None:
                    break
        return e


def alert_on_fail(method, alert: Alert = Alert()):
    @functools.wraps(method)
    async def _impl(self, *method_args, **method_kwargs):
        try:
            return await method(self, *method_args, **method_kwargs)
        except BaseException as e:
            await alert_service.handle(e, alert)

    return _impl
