"""
Типизированное хранилище «ключ → dataclass» в Redis.

Основной API — :class:`RedisService` и фабрика ``make_map``, которая возвращает :class:`KVMap`:
все значения лежат в одном Redis-hash (``HSET``/``HGET``), сериализация через ``pickle`` поверх
``asdict`` (или сырого объекта, если это не dataclass).

Ключи в hash имеют вид ``{key_prefix}:{user_key}`` (по умолчанию prefix ``_``).
Имя hash: ``{app_name}:{hname}``, где ``app_name`` берётся из :class:`ConfigService`.

Записи с ``ttl`` сохраняются отдельным строковым ключом ``{hname}:ttl:{field_key}`` с ``SETEX``,
потому что у полей Redis-hash нет собственного TTL.

Локальный Redis: ``materials/redis/docker-compose.yml`` → ``docker compose up -d``.
"""
from __future__ import annotations

import pickle
import socket
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, Generic, Optional, Tuple, Type, TypeVar

import dacite
from paprika import singleton
from redis.client import Redis

from src.mybootstrap_ioc_itskovichanton.config import ConfigService
from src.mybootstrap_ioc_itskovichanton.ioc import bean
from src.mybootstrap_mvc_itskovichanton.exceptions import CoreException

T = TypeVar("T")


@dataclass
class RedisConfig:
    """Параметры подключения к Redis (секция ``redis`` в config.yml или значения по умолчанию)."""

    host: str = "localhost"
    port: int = 6379
    password: str | None = None


def default_deserializer(value_class: type, value_dict: dict) -> Any:
    """Собирает dataclass из dict после ``pickle.loads`` (нестрогая dacite-конфигурация)."""
    return dacite.from_dict(
        data_class=value_class,
        data=value_dict,
        config=dacite.Config(strict=False, check_types=False),
    )


@bean(config=("redis", RedisConfig, RedisConfig()))
class RedisService:
    """
    Сервис доступа к Redis для приложения.

    Предоставляет проверку доступности, синглтон-клиент ``redis.Redis`` и фабрику типизированных map'ов.
    """

    config_service: ConfigService

    def get_address(self) -> str:
        """Строка ``host:port`` для логов и health-check."""
        return f"{self.config.host}:{self.config.port}"

    def check_availability(self, timeout: float = 1.0) -> None:
        """
        Проверяет, что Redis отвечает на PING по TCP (без использования redis-py).

        :raises CoreException: если ответ не содержит PONG.
        """
        with socket.create_connection((self.config.host, self.config.port), timeout=timeout) as conn:
            conn.sendall(b"*1\r\n$4\r\nPING\r\n")
            reply = conn.recv(1024)
            if b"PONG" not in reply:
                raise CoreException(message=f"redis responded on PING: {str(reply)}")

    @singleton
    def get(self) -> Redis:
        """Возвращает общий клиент Redis (db=0)."""
        return Redis(host=self.config.host, port=self.config.port, db=0, password=self.config.password)

    def make_map(
        self,
        value_class: Type[T],
        hname: str,
        key_prefix: str | None = None,
        deserializer: Callable[[type, dict], Any] = default_deserializer,
        pre_serializer: Callable[[Any], Any] = lambda x: x,
    ) -> "KVMap[T]":
        """
        Создаёт типизированную map «логический ключ → value_class`` в Redis.

        :param value_class: класс значения (обычно dataclass).
        :param hname: суффикс имени hash (к ``app_name``).
        :param key_prefix: префикс полей внутри hash.
        :param deserializer: dict → объект после распаковки pickle.
        :param pre_serializer: преобразование значения перед ``asdict``.
        """
        full_hname = f"{self.config_service.app_name()}:{hname}"
        if not key_prefix:
            key_prefix = "_"
        return KVMap(
            rds=self.get(),
            hname=full_hname,
            key_prefix=key_prefix,
            value_class=value_class,
            deserializer=deserializer,
            pre_serializer=pre_serializer,
        )


class KVMap(Generic[T]):
    """
    Одна логическая коллекция ключей в Redis (один hash + опциональные TTL-ключи).
    """

    def __init__(
        self,
        rds: Redis,
        hname: str,
        key_prefix: str,
        value_class: Type[T],
        deserializer: Callable[[type, dict], Any],
        pre_serializer: Callable[[Any], Any],
    ):
        self.rds = rds
        self.hname = hname
        self.key_prefix = key_prefix
        self.value_class = value_class
        self.deserializer = deserializer
        self.pre_serializer = pre_serializer

    def _make_key(self, key: str) -> str:
        """Физическое имя поля в hash или суффикс TTL-ключа."""
        return f"{self.key_prefix}:{key}"

    def _ttl_redis_key(self, field_key: str) -> str:
        """Отдельный строковый ключ Redis для значения с ограниченным временем жизни."""
        return f"{self.hname}:ttl:{field_key}"

    def _strip_prefix(self, field_key: str) -> str:
        """Убирает ``key_prefix:`` из имени поля hash."""
        prefix = f"{self.key_prefix}:"
        if field_key.startswith(prefix):
            return field_key[len(prefix):]
        return field_key

    def _serialize(self, value: T) -> bytes:
        value = self.pre_serializer(value)
        try:
            value_dict = asdict(value)
        except TypeError:
            value_dict = value
        return pickle.dumps(value_dict)

    def _deserialize(self, value_bytes: bytes, vc: Type | None = None) -> T:
        value_dict = pickle.loads(value_bytes)
        if self.deserializer:
            return self.deserializer(vc or self.value_class, value_dict)
        return value_dict

    def get(self, key: str, vc: Type | None = None) -> T | None:
        """
        Читает значение по логическому ключу.

        Сначала hash-поле, затем TTL-строка (если запись создавалась с ``ttl``).
        """
        field_key = self._make_key(key)
        value_bytes = self.rds.hget(self.hname, field_key)
        if value_bytes is None:
            value_bytes = self.rds.get(self._ttl_redis_key(field_key))
        if value_bytes is None:
            return None
        return self._deserialize(value_bytes, vc)

    def set(self, key: str, value: T, ttl: int | None = None) -> None:
        """
        Сохраняет значение.

        Без ``ttl`` — ``HSET`` в hash; с ``ttl`` — ``SETEX`` на отдельном ключе (поля hash не поддерживают TTL).
        """
        value_bytes = self._serialize(value)
        field_key = self._make_key(key)
        if ttl:
            self.rds.setex(self._ttl_redis_key(field_key), ttl, value_bytes)
        else:
            self.rds.hset(self.hname, field_key, value_bytes)

    def update(self, key: str, updater: Callable[[T], Any]) -> T:
        """
        Читает значение (или создаёт пустой ``value_class()``), применяет ``updater``, сохраняет обратно.
        """
        v = self.get(key)
        if v is None:
            v = self.value_class()
        updater(v)
        self.set(key, v)
        return v

    def get_keys(self) -> list[str]:
        """Список логических ключей (поля hash + неистёкшие TTL-записи)."""
        keys = set()
        for raw in self.rds.hkeys(self.hname):
            field_key = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            keys.add(self._strip_prefix(field_key))

        pattern = f"{self.hname}:ttl:{self.key_prefix}:*"
        for raw in self.rds.scan_iter(match=pattern, count=100):
            key_str = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            suffix = key_str[len(f"{self.hname}:ttl:"):]
            keys.add(self._strip_prefix(suffix))
        return sorted(keys)

    def delete(self, key: str) -> int:
        """Удаляет запись из hash и TTL-ключа; возвращает число удалённых ключей Redis."""
        field_key = self._make_key(key)
        removed = self.rds.hdel(self.hname, field_key)
        removed += self.rds.delete(self._ttl_redis_key(field_key))
        return removed

    def find(
        self, finder: Callable[[str, T], bool] | None = None
    ) -> Tuple[str, T] | None:
        """
        Возвращает первую пару ``(логический_ключ, значение)``, для которой ``finder`` истинен.

        Если ``finder`` не задан — берётся первая запись из ``get_all``.
        """
        if finder is None:
            finder = lambda _k, _v: True
        for logical_key, value in self.get_all().items():
            if finder(logical_key, value):
                return logical_key, value
        return None

    def get_all(self, filter: Callable[[str, T], bool] | None = None) -> Dict[str, T]:
        """Все записи map, опционально отфильтрованные ``filter(key, value)``."""
        if filter is None:
            filter = lambda _k, _v: True
        result: Dict[str, T] = {}
        for raw_key, value_bytes in self.rds.hgetall(self.hname).items():
            field_key = raw_key.decode("utf-8") if isinstance(raw_key, bytes) else raw_key
            logical_key = self._strip_prefix(field_key)
            value = self._deserialize(value_bytes)
            if filter(logical_key, value):
                result[logical_key] = value

        pattern = f"{self.hname}:ttl:{self.key_prefix}:*"
        for raw in self.rds.scan_iter(match=pattern, count=100):
            key_str = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            field_key = key_str[len(f"{self.hname}:ttl:"):]
            logical_key = self._strip_prefix(field_key)
            if logical_key in result:
                continue
            value_bytes = self.rds.get(raw)
            if value_bytes is None:
                continue
            value = self._deserialize(value_bytes)
            if filter(logical_key, value):
                result[logical_key] = value
        return result

    def clear(self) -> None:
        """Удаляет hash и все TTL-ключи этой map."""
        self.rds.delete(self.hname)
        pattern = f"{self.hname}:ttl:{self.key_prefix}:*"
        for raw in self.rds.scan_iter(match=pattern, count=100):
            self.rds.delete(raw)
