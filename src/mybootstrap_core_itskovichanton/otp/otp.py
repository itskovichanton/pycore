import email
from email import policy
from email.message import EmailMessage
from dataclasses import dataclass
from typing import Protocol, Sequence, Callable
from time import sleep
from datetime import datetime, timedelta

from imapclient import IMAPClient, SEEN

from src.mybootstrap_ioc_itskovichanton.ioc import bean
from src.mybootstrap_mvc_itskovichanton.exceptions import CoreException, ERR_REASON_TECHNICAL
from src.mybootstrap_core_itskovichanton.logger import log


@dataclass
class IMAPConfig:
    host: str
    port: int
    username: str
    password: str


@dataclass
class OTPClientConfig:
    subject: str
    sender: str
    folder: str = 'INBOX'
    unread: bool = True
    msg_type: str = 'html'
    wait: int = 5
    timeout: int = 60


class OTPClient(Protocol):
    def get_otp(self, since: datetime, parse: Callable[[str], str | None]) -> list[str]:
        """Читать сообщения свежее <since> каждые <wait> секунд до получения OTP или наступления <timeout>."""


@bean(config=('gsfr.otp', OTPClientConfig), imap_config=('imap', IMAPConfig))
class MailOTPClient(OTPClient):
    """Ищет OTP на почте"""
    def init(self):
        if self.config.msg_type not in ('html', 'plain'):
            raise CoreException('Only "html" and "plain" msg types are supported.', reason=ERR_REASON_TECHNICAL)

        if self.config.wait < 1:
            self.config.wait = 1

        if self.config.timeout < 1:
            self.config.timeout = 1

    def get_otp(self, since: datetime, parse: Callable[[str], str | None]) -> list[str]:
        """Возвращает все подходящие сообщения"""
        since = since.replace(microsecond=0)
        if since.tzinfo is None:
            since = since.astimezone()

        with self._connect() as client:
            stop = datetime.now() + timedelta(seconds=self.config.timeout)
            while datetime.now() < stop:
                sleep(self.config.wait)  # чтобы OTP пришёл

                uids, msgs = self._fresh_messages(client, since)
                if len(msgs) > 0:
                    try:
                        otps = [self._parse_otp(msg, parse) for msg in msgs]
                    finally:
                        self._read_msgs(client, uids)
                    return otps

        raise CoreException(f'Did not receive OTP in {self.config.timeout}s.', ERR_REASON_TECHNICAL)

    def _fresh_messages(self, client: IMAPClient, since: datetime) -> tuple[Sequence[int], Sequence[EmailMessage]]:
        uids = self._search(client, since)
        if len(uids) > 0:
            msgs = self._fetch(client, uids)
            fresh = [msg for msg in msgs if self._is_fresh(msg[1], since)]
            if len(fresh) > 0:
                return tuple(zip(*fresh))

        return [], []

    @log('imap', _action='connect')
    def _connect(self) -> IMAPClient:
        client = IMAPClient(self.imap_config.host, port=self.imap_config.port, ssl=True)
        try:
            client.login(self.imap_config.username, self.imap_config.password)
            client.select_folder(self.config.folder)
            return client
        except Exception as e:
            client.__exit__(None, None, None)
            raise CoreException(message='Could not connect to IMAP server.', reason=ERR_REASON_TECHNICAL, cause=e)

    @log('imap', _action='search')
    def _search(self, client: IMAPClient, since: datetime) -> list[int]:
        criteria = ['UNSEEN'] if self.config.unread else ['ALL']
        criteria += ['FROM', self.config.sender, 'SUBJECT', self.config.subject, 'SINCE', since.date()]
        return client.search(criteria, charset='UTF-8')

    @log('imap', _action='fetch')
    def _fetch(self, client: IMAPClient, uids: list[int]) -> list[tuple[int, EmailMessage]]:
        data = client.fetch(uids, ['BODY.PEEK[]'])
        res = []
        for uid in uids:
            body = data.get(uid, {}).get(b'BODY[]', None)
            if body:
                msg = email.message_from_bytes(body, policy=policy.default)
                res.append((uid, msg))
        return res

    def _msg_date(self, msg: EmailMessage) -> datetime | None:
        if msg['Date']:
            date = msg['Date'].datetime
            if date and not date.tzinfo:
                date = date.astimezone()
            return date
        return None

    def _is_fresh(self, msg: EmailMessage, since: datetime) -> bool:
        date = self._msg_date(msg)
        if date is None:
            return False
        return date >= since

    def _parse_otp(self, msg: EmailMessage, parse: Callable) -> str:
        # выкидываем ошибки. Считаем, что фильтры выделят otp-сообщения.
        # если они не читаются, значит неверный формат или парсер.
        body = msg.get_body(preferencelist=(self.config.msg_type,))
        if body:
            content = body.get_content()
            if content:
                code = parse(content)
                if code:
                    return code
                raise CoreException('Could not parse OTP.', reason=ERR_REASON_TECHNICAL)
            raise CoreException(f'Msg {self.config.msg_type} body is empty', err_reason=ERR_REASON_TECHNICAL)
        raise CoreException(f'Msg does not have {self.config.msg_type} body', err_reason=ERR_REASON_TECHNICAL)

    @log('imap', _action='read')
    def _read_msgs(self, client: IMAPClient, uids: list[int]) -> None:
        try:
            client.add_flags(uids, [SEEN], silent=True)
        except Exception:
            pass
