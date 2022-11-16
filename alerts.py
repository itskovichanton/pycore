from dataclasses import dataclass
from typing import Protocol

from config import ConfigService
from email_service import EmailService, Params
from fr import FRService, Post
from utils import trim_string


@dataclass
class Alert:
    message: str
    subject: str
    byEmail: bool = True
    byFR: bool = True
    level: int = 1
    send: bool = True


class AlertService(Protocol):

    async def send(self, a: Alert):
        """Send alert"""


class AlertServiceImpl(AlertService):

    def __init__(self, config_service: ConfigService, fr_service: FRService, email_service: EmailService):
        self.config_service = config_service
        self.fr_service = fr_service
        self.email_service = email_service
        self.emails = self.config_service.config.settings["alerts"]["emails"]
        self.fromEmail = self.config_service.config.settings["email"]["from"]

    async def send(self, a: Alert):
        if not a.send:
            return

        a.subject = f"{self.config_service.app_name()} - {a.subject}"

        if a.byFR:
            await self.send_by_fr(a)

        if a.byEmail:
            self.send_by_email(a)

    async def send_by_fr(self, a):
        await self.fr_service.send(Post(project=a.subject, level=a.level, msg=trim_string(a.message, 4000)))

    def send_by_email(self, a):
        self.email_service.send(
            Params(subject=a.subject, toEmail=self.emails, senderEmail=self.fromEmail, content_plain=a.message))
