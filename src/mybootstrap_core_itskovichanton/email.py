import smtplib
import ssl
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Protocol

from src.mybootstrap_ioc_itskovichanton.ioc import bean


@dataclass
class EmailConfig:
    username: str
    password: str
    host: str
    address: str
    port: str
    encoding: str = "utf-8"


@dataclass
class Params:
    toEmail: list[str]
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

        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.set_ciphers('DEFAULT@SECLEVEL=1')
        server = smtplib.SMTP_SSL(self.config.host, int(self.config.port), context=context)
        server.command_encoding = self.config.encoding
        server.login(self.config.username, self.config.password)
        m = MIMEMultipart()
        m["From"] = a.senderEmail,
        m["To"] = ', '.join(a.toEmail)
        m["Subject"] = a.subject
        if a.content_plain:
            m.attach(MIMEText(a.content_plain, "plain/text", _charset=self.config.encoding))
        elif not a.content_html:
            m.attach(MIMEText(a.content_html, "html", _charset=self.config.encoding))

        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.set_ciphers('DEFAULT@SECLEVEL=1')
        return server.sendmail(a.senderEmail, m["To"], m.as_string())
