import json
import shlex
from typing import Optional, Union, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import urllib.parse

from src.mybootstrap_core_itskovichanton.utils import is_listable


class HttpMethod(Enum):
    """HTTP методы"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


CURL_CMD_DEFAULT = "curl"
CURL_CMD_ALT = "/usr/bin/curl"


class CurlBuilder:
    def __init__(self, url: Optional[str] = None):
        """
        Инициализация билдера curl команд

        Args:
            url: URL для запроса (можно указать позже через метод url())
        """
        self._ciphers: Optional[str] = None
        self._url: Optional[str] = url
        self._method: Optional[HttpMethod] = None
        self._headers: Dict[str, str] = {}
        self._cookies: Dict[str, str] = {}
        self._data: Optional[Union[str, Dict, List]] = None
        self._form_data: Dict[str, Union[str, List[str]]] = {}
        self._files: Dict[str, Union[str, tuple]] = {}
        self._json_data: Optional[Union[Dict, List]] = None
        self._timeout: Optional[int] = None
        self._connect_timeout: Optional[int] = None
        self._max_time: Optional[int] = None
        self._retry: Optional[int] = None
        self._retry_delay: Optional[int] = None
        self._retry_max_time: Optional[int] = None
        self._user_agent: Optional[str] = None
        self._referer: Optional[str] = None
        self._follow_redirects: bool = False
        self._max_redirects: Optional[int] = None
        self._location: bool = False
        self._proxy: Optional[str] = None
        self._proxy_user: Optional[str] = None
        self._insecure: bool = False
        self._cacert: Optional[str] = None
        self._cert: Optional[str] = None
        self._key: Optional[str] = None
        self._cert_type: Optional[str] = None
        self._key_type: Optional[str] = None
        self._key_password: Optional[str] = None
        self._output: Optional[str] = None
        self._silent: bool = False
        self._verbose: bool = False
        self._show_error: bool = False
        self._include_headers: bool = False
        self._compressed: bool = False
        self._basic_auth: Optional[tuple] = None
        self._bearer_token: Optional[str] = None
        self._custom_options: List[str] = []
        self._store_headers: Optional[str] = None
        self._command = "curl"

    def command(self, command: str) -> 'CurlBuilder':
        self._command = command
        return self

    def url(self, url: str) -> 'CurlBuilder':
        """
        Установка URL

        Args:
            url: URL для запроса

        Returns:
            self для цепочки вызовов
        """
        self._url = url
        return self

    def ciphers(self, ciphers: str) -> 'CurlBuilder':
        """
        Установка URL

        Args:
            url: URL для запроса

        Returns:
            self для цепочки вызовов
        """
        self._ciphers = ciphers
        return self

    def store_headers_file(self, filename: str) -> 'CurlBuilder':
        """
        Установка URL

        Args:
            url: URL для запроса

        Returns:
            self для цепочки вызовов
        """
        self._store_headers = filename
        return self

    def method(self, method: Union[HttpMethod, str]) -> 'CurlBuilder':
        """
        Установка HTTP метода

        Args:
            method: HTTP метод (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)

        Returns:
            self для цепочки вызовов
        """
        if isinstance(method, str):
            method = HttpMethod(method.upper())
        self._method = method
        return self

    def header(self, name: str, value: str) -> 'CurlBuilder':
        """
        Добавление заголовка

        Args:
            name: Имя заголовка
            value: Значение заголовка

        Returns:
            self для цепочки вызовов
        """
        self._headers[name] = value
        return self

    def headers(self, headers: Dict[str, str]) -> 'CurlBuilder':
        """
        Установка нескольких заголовков

        Args:
            headers: Словарь заголовков

        Returns:
            self для цепочки вызовов
        """
        self._headers.update(headers)
        return self

    def cookie(self, name: str, value: str) -> 'CurlBuilder':
        """
        Добавление куки

        Args:
            name: Имя куки
            value: Значение куки

        Returns:
            self для цепочки вызовов
        """
        self._cookies[name] = value
        return self

    def cookies(self, cookies: Dict[str, str]) -> 'CurlBuilder':
        """
        Установка нескольких куки

        Args:
            cookies: Словарь куки

        Returns:
            self для цепочки вызовов
        """
        self._cookies.update(cookies)
        return self

    def data(self, data: Union[str, Dict, List]) -> 'CurlBuilder':
        """
        Установка данных для POST/PUT запроса (application/x-www-form-urlencoded)

        Args:
            data: Данные в виде строки, словаря или списка

        Returns:
            self для цепочки вызовов
        """
        self._data = data
        return self

    def form(self, name: str, value: Union[str, List[str]]) -> 'CurlBuilder':
        """
        Добавление поля формы (multipart/form-data)

        Args:
            name: Имя поля
            value: Значение поля (может быть списком)

        Returns:
            self для цепочки вызовов
        """
        self._form_data[name] = value
        return self

    def forms(self, form_data: Dict[str, Union[str, List[str]]]) -> 'CurlBuilder':
        """
        Добавление нескольких полей формы

        Args:
            form_data: Словарь полей формы

        Returns:
            self для цепочки вызовов
        """
        self._form_data.update(form_data)
        return self

    def file(self, field_name: str, file_path: str, mime_type: str = None) -> 'CurlBuilder':
        """
        Добавление файла для загрузки

        Args:
            field_name: Имя поля для файла
            file_path: Путь к файлу
            mime_type: MIME-тип файла (опционально)

        Returns:
            self для цепочки вызовов
        """
        if mime_type:
            self._files[field_name] = (file_path, mime_type)
        else:
            self._files[field_name] = file_path
        return self

    def json(self, data: Union[Dict, List]) -> 'CurlBuilder':
        """
        Установка JSON данных для запроса

        Args:
            data: JSON данные

        Returns:
            self для цепочки вызовов
        """
        self._json_data = data
        return self

    def timeout(self, seconds: int) -> 'CurlBuilder':
        """
        Общий таймаут запроса

        Args:
            seconds: Таймаут в секундах

        Returns:
            self для цепочки вызовов
        """
        self._timeout = seconds
        return self

    def connect_timeout(self, seconds: int) -> 'CurlBuilder':
        """
        Таймаут подключения

        Args:
            seconds: Таймаут в секундах

        Returns:
            self для цепочки вызовов
        """
        self._connect_timeout = seconds
        return self

    def max_time(self, seconds: int) -> 'CurlBuilder':
        """
        Максимальное время выполнения запроса

        Args:
            seconds: Время в секундах

        Returns:
            self для цепочки вызовов
        """
        self._max_time = seconds
        return self

    def retry(self, times: int, delay: int = 0, max_time: int = None) -> 'CurlBuilder':
        """
        Настройка повторных попыток

        Args:
            times: Количество попыток
            delay: Задержка между попытками в секундах
            max_time: Максимальное время для повторных попыток

        Returns:
            self для цепочки вызовов
        """
        self._retry = times
        self._retry_delay = delay
        self._retry_max_time = max_time
        return self

    def user_agent(self, user_agent: str) -> 'CurlBuilder':
        """
        Установка User-Agent

        Args:
            user_agent: User-Agent строка

        Returns:
            self для цепочки вызовов
        """
        self._user_agent = user_agent
        return self

    def referer(self, referer: str) -> 'CurlBuilder':
        """
        Установка Referer

        Args:
            referer: Referer URL

        Returns:
            self для цепочки вызовов
        """
        self._referer = referer
        return self

    def follow_redirects(self, max_redirects: int = None) -> 'CurlBuilder':
        """
        Следование редиректам

        Args:
            max_redirects: Максимальное количество редиректов

        Returns:
            self для цепочки вызовов
        """
        self._follow_redirects = True
        self._max_redirects = max_redirects
        return self

    def location(self, enabled: bool = True) -> 'CurlBuilder':
        """
        Вывод URL после редиректов

        Args:
            enabled: Включить опцию

        Returns:
            self для цепочки вызовов
        """
        self._location = enabled
        return self

    def proxy(self, proxy_url: str, username: str = None, password: str = None) -> 'CurlBuilder':
        """
        Настройка прокси

        Args:
            proxy_url: URL прокси
            username: Имя пользователя (опционально)
            password: Пароль (опционально)

        Returns:
            self для цепочки вызовов
        """
        self._proxy = proxy_url
        if username:
            self._proxy_user = f"{username}:{password}" if password else username
        return self

    def insecure(self, enabled: bool = True) -> 'CurlBuilder':
        """
        Отключение проверки SSL сертификатов

        Args:
            enabled: Включить небезопасный режим

        Returns:
            self для цепочки вызовов
        """
        self._insecure = enabled
        return self

    def cacert(self, cert_file: str) -> 'CurlBuilder':
        """
        Установка CA сертификата

        Args:
            cert_file: Путь к файлу с CA сертификатами

        Returns:
            self для цепочки вызовов
        """
        self._cacert = cert_file
        return self

    def cert(self, cert_file: str, key_file: str = None, cert_type: str = None,
             key_type: str = None, key_password: str = None) -> 'CurlBuilder':
        """
        Настройка клиентского сертификата

        Args:
            cert_file: Путь к файлу сертификата
            key_file: Путь к файлу приватного ключа
            cert_type: Тип сертификата (PEM, DER, ENG)
            key_type: Тип ключа (PEM, DER, ENG)
            key_password: Пароль к ключу

        Returns:
            self для цепочки вызовов
        """
        self._cert = cert_file
        self._key = key_file
        self._cert_type = cert_type
        self._key_type = key_type
        self._key_password = key_password
        return self

    def output(self, file_path: str) -> 'CurlBuilder':
        """
        Сохранение ответа в файл

        Args:
            file_path: Путь к файлу для сохранения

        Returns:
            self для цепочки вызовов
        """
        self._output = file_path
        return self

    def silent(self, enabled: bool = True) -> 'CurlBuilder':
        """
        Тихий режим (без прогресс-бара)

        Args:
            enabled: Включить тихий режим

        Returns:
            self для цепочки вызовов
        """
        self._silent = enabled
        return self

    def verbose(self, enabled: bool = True) -> 'CurlBuilder':
        """
        Подробный вывод

        Args:
            enabled: Включить подробный вывод

        Returns:
            self для цепочки вызовов
        """
        self._verbose = enabled
        return self

    def show_error(self, enabled: bool = True) -> 'CurlBuilder':
        """
        Показывать ошибки даже в тихом режиме

        Args:
            enabled: Включить показ ошибок

        Returns:
            self для цепочки вызовов
        """
        self._show_error = enabled
        return self

    def include_headers(self, enabled: bool = True) -> 'CurlBuilder':
        """
        Включение заголовков в вывод

        Args:
            enabled: Включить заголовки в вывод

        Returns:
            self для цепочки вызовов
        """
        self._include_headers = enabled
        return self

    def compressed(self, enabled: bool = True) -> 'CurlBuilder':
        """
        Запрос сжатого ответа

        Args:
            enabled: Включить сжатие

        Returns:
            self для цепочки вызовов
        """
        self._compressed = enabled
        return self

    def basic_auth(self, username: str, password: str) -> 'CurlBuilder':
        """
        Базовая аутентификация

        Args:
            username: Имя пользователя
            password: Пароль

        Returns:
            self для цепочки вызовов
        """
        self._basic_auth = (username, password)
        return self

    def bearer_token(self, token: str) -> 'CurlBuilder':
        """
        Bearer токен авторизации

        Args:
            token: Bearer токен

        Returns:
            self для цепочки вызовов
        """
        self._bearer_token = token
        return self

    def option(self, option: str) -> 'CurlBuilder':
        """
        Добавление пользовательской опции curl

        Args:
            option: Опция curl

        Returns:
            self для цепочки вызовов
        """
        self._custom_options.append(option)
        return self

    def _escape_shell_arg(self, arg: str) -> str:
        """
        Экранирование аргумента для shell

        Args:
            arg: Аргумент для экранирования

        Returns:
            Экранированная строка
        """
        # Используем shlex.quote для безопасного экранирования
        return shlex.quote(arg)

    def _escape_json_for_shell(self, json_data: Union[Dict, List]) -> str:
        """
        Правильное экранирование JSON для shell

        Args:
            json_data: JSON данные

        Returns:
            Экранированная JSON строка
        """
        # Сначала преобразуем в JSON строку
        json_str = json.dumps(json_data, ensure_ascii=False)
        # Затем экранируем для shell
        return self._escape_shell_arg(json_str)

    def _build_cookies_string(self) -> str:
        """
        Построение строки куки из словаря

        Returns:
            Строка куки для curl
        """
        if not self._cookies:
            return ""

        cookies_parts = []
        for name, value in self._cookies.items():
            # Экранируем специальные символы в значении
            escaped_value = str(value).replace(';', r'\;')
            cookies_parts.append(f"{name}={escaped_value}")

        return "; ".join(cookies_parts)

    def build(self) -> str:
        """
        Построение команды curl

        Returns:
            Готовая команда curl
        """
        if not self._url:
            raise ValueError("URL не установлен. Используйте метод url() для его установки.")

        parts = [self._command or "curl"]

        # Метод запроса
        if self._method:
            parts.append(f"-X {self._method.value}")

        # Заголовки
        for name, value in self._headers.items():
            # Экранируем значение, если оно содержит кавычки
            if not is_listable(value):
                value = [value]
            for v in value:
                escaped_value = v.replace('"', r'\"')
                parts.append(f'-H "{name}: {escaped_value}"')

        # Куки
        cookies_str = self._build_cookies_string()
        if cookies_str:
            parts.append(f'--cookie "{cookies_str}"')

        # Данные
        if self._data is not None:
            if isinstance(self._data, dict):
                # Формируем application/x-www-form-urlencoded
                encoded_data = urllib.parse.urlencode(self._data, doseq=True)
                parts.append(f"--data {self._escape_shell_arg(encoded_data)}")
            elif isinstance(self._data, list):
                # Список пар ключ-значение
                encoded_data = urllib.parse.urlencode(self._data, doseq=True)
                parts.append(f"--data {self._escape_shell_arg(encoded_data)}")
            else:
                # Простая строка
                parts.append(f"--data {self._escape_shell_arg(str(self._data))}")

        # Форма (multipart/form-data)
        if self._form_data:
            for name, value in self._form_data.items():
                if isinstance(value, list):
                    for v in value:
                        parts.append(f'--form "{name}={v}"')
                else:
                    parts.append(f'--form "{name}={value}"')

        # Файлы
        if self._files:
            for field_name, file_info in self._files.items():
                if isinstance(file_info, tuple):
                    file_path, mime_type = file_info
                    parts.append(f'--form "{field_name}=@{file_path};type={mime_type}"')
                else:
                    parts.append(f'--form "{field_name}=@{file_info}"')

        # JSON данные
        if self._json_data is not None:
            json_str = self._escape_json_for_shell(self._json_data)
            parts.append(f"--data {json_str}")
            # Добавляем заголовок Content-Type если не установлен
            if "Content-Type" not in [h.lower() for h in self._headers.keys()]:
                parts.append('-H "Content-Type: application/json"')

        # Таймауты
        if self._timeout is not None:
            parts.append(f"--max-time {self._timeout}")

        if self._connect_timeout is not None:
            parts.append(f"--connect-timeout {self._connect_timeout}")

        if self._max_time is not None:
            parts.append(f"--max-time {self._max_time}")

        # Повторные попытки
        if self._retry is not None:
            parts.append(f"--retry {self._retry}")
            if self._retry_delay is not None:
                parts.append(f"--retry-delay {self._retry_delay}")
            if self._retry_max_time is not None:
                parts.append(f"--retry-max-time {self._retry_max_time}")

        # User-Agent
        if self._user_agent:
            parts.append(f'-A "{self._user_agent}"')

        # Referer
        if self._referer:
            parts.append(f'-E "{self._referer}"')
            parts.append(f'--cert-type P12')

        # Редиректы
        if self._follow_redirects:
            parts.append("-L")
            if self._max_redirects is not None:
                parts.append(f"--max-redirs {self._max_redirects}")

        if self._location:
            parts.append("--location")

        # Прокси
        if self._proxy:
            parts.append(f"--proxy {self._escape_shell_arg(self._proxy)}")
            if self._proxy_user:
                parts.append(f'--proxy-user "{self._proxy_user}"')

        # SSL/сертификаты
        if self._insecure:
            parts.append("--insecure")

        if self._cacert:
            parts.append(f"--cacert {self._escape_shell_arg(self._cacert)}")

        if self._cert:
            cert_parts = [f"--cert {self._escape_shell_arg(self._cert)}"]
            if self._key:
                cert_parts.append(f"--key {self._escape_shell_arg(self._key)}")
            if self._cert_type:
                cert_parts.append(f"--cert-type {self._cert_type}")
            if self._key_type:
                cert_parts.append(f"--key-type {self._key_type}")
            if self._key_password:
                cert_parts.append(f'--pass "{self._key_password}"')
            parts.extend(cert_parts)

        # Вывод
        if self._output:
            parts.append(f"--output {self._escape_shell_arg(self._output)}")

        # Флаги вывода
        if self._silent:
            parts.append("--silent")

        if self._verbose:
            parts.append("--verbose")

        if self._ciphers:
            parts.append(f"--ciphers {self._ciphers}")

        if self._store_headers:
            parts.append(f"-D {self._store_headers}")

        if self._show_error:
            parts.append("--show-error")

        if self._include_headers:
            parts.append("--include")

        if self._compressed:
            parts.append("--compressed")

        # Аутентификация
        if self._basic_auth:
            username, password = self._basic_auth
            parts.append(f'--user "{username}:{password}"')

        if self._bearer_token:
            parts.append(f'--header "Authorization: Bearer {self._bearer_token}"')

        # Пользовательские опции
        parts.extend(self._custom_options)

        # URL в конце
        parts.append(self._escape_shell_arg(self._url))

        return " ".join(parts)

    def build_as_list(self) -> List[str]:
        """
        Построение команды curl в виде списка аргументов

        Returns:
            Список аргументов для subprocess
        """
        if not self._url:
            raise ValueError("URL не установлен")

        args = ["curl"]

        # Метод запроса
        if self._method:
            args.extend(["-X", self._method.value])

        # Заголовки
        for name, value in self._headers.items():
            args.extend(["-H", f"{name}: {value}"])

        # Куки
        cookies_str = self._build_cookies_string()
        if cookies_str:
            args.extend(["--cookie", cookies_str])

        # Данные
        if self._data is not None:
            if isinstance(self._data, dict):
                encoded_data = urllib.parse.urlencode(self._data, doseq=True)
                args.extend(["--data", encoded_data])
            elif isinstance(self._data, list):
                encoded_data = urllib.parse.urlencode(self._data, doseq=True)
                args.extend(["--data", encoded_data])
            else:
                args.extend(["--data", str(self._data)])

        # Форма
        if self._form_data:
            for name, value in self._form_data.items():
                if isinstance(value, list):
                    for v in value:
                        args.extend(["--form", f"{name}={v}"])
                else:
                    args.extend(["--form", f"{name}={value}"])

        # Файлы
        if self._files:
            for field_name, file_info in self._files.items():
                if isinstance(file_info, tuple):
                    file_path, mime_type = file_info
                    args.extend(["--form", f"{field_name}=@{file_path};type={mime_type}"])
                else:
                    args.extend(["--form", f"{field_name}=@{file_info}"])

        # JSON данные
        if self._json_data is not None:
            json_str = json.dumps(self._json_data, ensure_ascii=False)
            args.extend(["--data", json_str])
            if "Content-Type" not in [h.lower() for h in self._headers.keys()]:
                args.extend(["-H", "Content-Type: application/json"])

        # Таймауты
        if self._timeout is not None:
            args.extend(["--max-time", str(self._timeout)])

        if self._connect_timeout is not None:
            args.extend(["--connect-timeout", str(self._connect_timeout)])

        # Другие опции...
        if self._user_agent:
            args.extend(["-A", self._user_agent])

        if self._follow_redirects:
            args.append("-L")
            if self._max_redirects is not None:
                args.extend(["--max-redirs", str(self._max_redirects)])

        if self._insecure:
            args.append("--insecure")

        if self._output:
            args.extend(["--output", self._output])

        if self._silent:
            args.append("--silent")

        if self._verbose:
            args.append("--verbose")

        if self._basic_auth:
            username, password = self._basic_auth
            args.extend(["--user", f"{username}:{password}"])

        # Пользовательские опции
        for opt in self._custom_options:
            args.append(opt)

        # URL в конце
        args.append(self._url)

        return args

    def get_command_summary(self) -> Dict[str, Any]:
        """
        Получение сводки команды без построения полной строки

        Returns:
            Словарь с информацией о команде
        """
        return {
            "url": self._url,
            "method": self._method.value if self._method else "GET",
            "headers": self._headers,
            "cookies": self._cookies,
            "has_data": self._data is not None,
            "has_json": self._json_data is not None,
            "has_form": bool(self._form_data),
            "has_files": bool(self._files),
            "timeout": self._timeout,
            "follow_redirects": self._follow_redirects,
            "insecure": self._insecure,
            "output_file": self._output,
            "auth_method": "basic" if self._basic_auth else "bearer" if self._bearer_token else "none"
        }

    def get_output(self):
        return self._output


# Примеры использования
if __name__ == "__main__":
    print("=== Пример 1: Простой GET запрос ===")
    curl1 = CurlBuilder("https://httpbin.org/get")
    print(curl1.build())

    print("\n=== Пример 2: POST с JSON данными ===")
    curl2 = (CurlBuilder("https://httpbin.org/post")
             .method("POST")
             .json({"name": "John", "age": 30, "city": "New York"})
             .header("X-Custom-Header", "MyValue")
             .verbose())
    print(curl2.build())

    print("\n=== Пример 3: POST с формой и файлами ===")
    curl3 = (CurlBuilder("https://httpbin.org/post")
             .method("POST")
             .form("username", "john_doe")
             .form("role", ["admin", "user"])  # Несколько значений для одного поля
             .file("avatar", "/path/to/avatar.jpg", "image/jpeg")
             .file("document", "/path/to/doc.pdf")
             .follow_redirects(5)
             .timeout(30))
    print(curl3.build())

    print("\n=== Пример 4: Сложный запрос с аутентификацией ===")
    curl4 = (CurlBuilder("https://api.example.com/data")
             .method("PUT")
             .json({"id": 123, "status": "updated"})
             .bearer_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
             .header("X-API-Version", "2.0")
             .cookie("session_id", "abc123def456")
             .cookie("user_prefs", 'theme=dark;language=en')
             .insecure()  # Для тестового сервера с самоподписанным сертификатом
             .connect_timeout(10)
             .max_time(60)
             .output("/tmp/response.json")
             .show_error())
    print(curl4.build())

    print("\n=== Пример 5: Запрос с сертификатами и прокси ===")
    curl5 = (CurlBuilder("https://secure.example.com/api")
             .method("POST")
             .cert("/path/to/client.crt", "/path/to/client.key", "PEM", "PEM", "mypassword")
             .cacert("/path/to/ca-bundle.crt")
             .proxy("http://proxy.company.com:8080", "user", "password")
             .compressed()
             .include_headers())
    print(curl5.build())

    print("\n=== Пример 6: Использование build_as_list для subprocess ===")
    curl6 = (CurlBuilder("https://httpbin.org/get")
             .header("Accept", "application/json")
             .user_agent("MyCurlClient/1.0"))

    cmd_list = curl6.build_as_list()
    print("Команда как список:")
    print(cmd_list)

    # Использование с subprocess
    import subprocess

    print("\nЗапуск команды через subprocess:")
    result = subprocess.run(cmd_list, capture_output=True, text=True)
    print(f"Код возврата: {result.returncode}")
    print(f"Вывод: {result.stdout[:200]}...")

    print("\n=== Пример 7: Сводка команды ===")
    summary = curl4.get_command_summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    print("\n=== Пример 8: Обработка специальных символов ===")
    curl8 = (CurlBuilder("https://api.example.com/test")
             .method("POST")
             .json({
        "message": 'Строка с "кавычками" и \\обратным слешем\\',
        "special": "& $ ` ; |"
    })
             .data({"param": 'value with "quotes"'}))
    print(curl8.build())
