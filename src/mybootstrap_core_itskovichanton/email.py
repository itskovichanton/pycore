import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from src.mybootstrap_ioc_itskovichanton.ioc import bean
from typing import Protocol


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
    subject: str
    content_plain: str = ""
    content_html: str = ""


class EmailService(Protocol):

    def send(self, a: Params):
        """Send email"""


@bean(config=("email", EmailConfig, None))
class EmailServiceImpl(EmailService):

    def send(self, a: Params):
        if self.config is None or not (a.content_plain or a.content_html):
            return

        msg = MIMEMultipart()
        msg['To'] = ",".join(a.toEmail) if type(a.toEmail) == list else a.toEmail
        msg['Subject'] = a.subject
        msg.attach(MIMEText(a.content_plain, 'plain'))

        # устанавливаем соединение с SMTP-сервером и отправляем сообщение
        server = smtplib.SMTP(self.config.host, self.config.port)
        server.login(self.config.username, self.config.password)
        text = msg.as_string()
        server.sendmail(from_addr=self.config.from_address,
                        to_addrs=a.toEmail,
                        msg=text)
        server.quit()
