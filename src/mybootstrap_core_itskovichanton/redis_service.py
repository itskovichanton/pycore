import pickle
from dataclasses import dataclass, asdict
from typing import TypeVar, Generic, Dict, Callable, Any

import dacite
from paprika import singleton
from redis.client import Redis
from src.mybootstrap_ioc_itskovichanton.config import ConfigService
from src.mybootstrap_ioc_itskovichanton.ioc import bean


@dataclass
class RedisConfig:
    host: str = "localhost"
    port: int = 6379
    password: str = None


def default_deserializer(value_class, value_dict):
    return dacite.from_dict(data_class=value_class, data=value_dict, config=dacite.Config(strict=False, check_types=False))


@bean(config=("redis", RedisConfig, RedisConfig()))
class RedisService:
    config_service: ConfigService

    @singleton
    def get(self) -> Redis:
        return Redis(host=self.config.host, port=self.config.port, db=0, password=self.config.password)

    def make_map(self, value_class: type, hname: str, key_prefix=None, deserializer=default_deserializer,
                 pre_serializer=lambda x: x):

        hname = f"{self.config_service.app_name()}:{hname}"
        if not key_prefix:
            key_prefix = "_"
        value_class_tv = TypeVar('value_class_tv')

        class KVMap(Generic[value_class_tv]):

            def __init__(self, rds: Redis):
                self.rds = rds

            @staticmethod
            def _make_key(key: str) -> str:
                return f"{key_prefix}:{key}"

            def get(self, key: str) -> value_class | None:
                value_bytes = self.rds.hget(hname, self._make_key(key))
                if value_bytes is None:
                    return None
                value_dict = pickle.loads(value_bytes)
                return deserializer(value_class, value_dict)

            def set(self, key: str, value: value_class):
                value = pre_serializer(value)
                value_dict = asdict(value)
                value_bytes = pickle.dumps(value_dict)
                self.rds.hset(hname, self._make_key(key), value_bytes)

            def update(self, key: str, updater: Callable[[value_class], Any]):
                v = self.get(key)
                if v is None:
                    v = value_class()
                updater(v)
                self.set(key, v)

            def delete(self, key: str):
                self.rds.delete(self._make_key(key))

            def get_all(self) -> Dict[str, value_class]:
                keys = self.rds.keys(f"{hname}:*")
                result = {}
                for key in keys:
                    key_str = key.decode('utf-8')
                    value_bytes = self.rds.hget(hname, self._make_key(key_str))
                    value_dict = pickle.loads(value_bytes)
                    result[key_str[len(hname) + 1:]] = deserializer(value_class, value_dict)
                return result

            def clear(self):
                self.rds.delete(hname)

        return KVMap(rds=self.get())
