import functools
import logging
import traceback
from dataclasses import dataclass
from typing import Protocol

from src.mybootstrap_core_itskovichanton.config import ConfigService
from src.mybootstrap_core_itskovichanton.email_service import EmailService, Params
from src.mybootstrap_core_itskovichanton.fr import FRService, Post
from src.mybootstrap_core_itskovichanton.ioc import bean
from src.mybootstrap_core_itskovichanton.utils import trim_string


@dataclass
class Alert:
    message: str = None
    subject: str = None
    byEmail: bool = True
    byFR: bool = True
    level: int = 1
    send: bool = True


class AlertService(Protocol):

    async def send(self, a: Alert):
        """Send alert"""

    async def handle(self, e: BaseException, alert: Alert = Alert()):
        """Send alert about exception"""


alert_service: AlertService


@bean
class AlertServiceImpl(AlertService):
    config_service: ConfigService
    fr_service: FRService
    email_service: EmailService

    def post_construct(self):
        self.emails = self.config_service.config.settings["alerts"]["emails"]
        self.from_email = self.config_service.config.settings["email"]["from"]

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
        logging.exception(e)
        alert.message = traceback.format_exc()
        alert.subject = "Exception"
        await self.send(alert)


def alert_on_fail(method, alert: Alert = Alert()):
    @functools.wraps(method)
    async def _impl(self, *method_args, **method_kwargs):
        try:
            return await method(self, *method_args, **method_kwargs)
        except BaseException as e:
            await alert_service.handle(e, alert)

    return _impl
