import smtplib
import ssl
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Protocol

from src.mybootstrap_core_itskovichanton.utils import is_listable
from src.mybootstrap_ioc_itskovichanton.ioc import bean


@dataclass
class EmailConfig:
    from_address: str
    username: str
    password: str
    host: str
    address: str
    port: str
    encoding: str = "utf-8"


@dataclass
class Params:
    toEmail: str | list[str]
    senderEmail: str
    subject: str
    content_plain: str = ""
    content_html: str = ""


class EmailService(Protocol):

    def send(self, a: Params):
        """Send email"""


@bean(config=("email", EmailConfig, None))
class EmailServiceImpl(EmailService):

    def send(self, a: Params):
        if self.config is None and not a.content_plain and not a.content_html:
            return

        msg = MIMEMultipart()
        msg['To'] = ",".join(a.toEmail) if is_listable(a.toEmail) else a.toEmail
        msg['Subject'] = a.subject

        # устанавливаем соединение с SMTP-сервером и отправляем сообщение
        server = smtplib.SMTP(self.config.host, self.config.port)
        server.login(self.config.username, self.config.password)
        text = msg.as_string()
        server.sendmail(from_addr=self.config.from_address,
                        to_addrs=a.toEmail,
                        msg=text)
        server.quit()
