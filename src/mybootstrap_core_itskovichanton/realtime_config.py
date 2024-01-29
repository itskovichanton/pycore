import os
import pickle
import threading

from etcd3 import Etcd3Client
from etcd3.events import PutEvent
from etcd3.exceptions import ConnectionFailedError
from etcd3.watch import WatchResponse
from fastapi_utils import camelcase
from retrying import retry

from src.mybootstrap_core_itskovichanton.events import Events
from src.mybootstrap_core_itskovichanton.validation import check_int, check_float, check_bool

os.putenv("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
from dataclasses import dataclass
from typing import Protocol, TypeVar, Generic, Any

import etcd3
from src.mybootstrap_ioc_itskovichanton.config import ConfigService
from src.mybootstrap_ioc_itskovichanton.ioc import bean, injector

T = TypeVar('T')


class RealTimeConfigEntry(Generic[T]):
    key: str
    _lock = threading.Lock()
    _value: T = None
    description: str = None
    watched: bool = False

    @property
    def value(self) -> T:
        with self._lock:
            return self._value

    @value.setter
    def value(self, value):
        with self._lock:
            self._value = value

    def deserialize_value(self, v: Any):
        return v


class IntRealTimeConfigEntry(RealTimeConfigEntry[int]):

    def deserialize_value(self, v):
        return check_int(self.key, v)


class FloatRealTimeConfigEntry(RealTimeConfigEntry[float]):

    def deserialize_value(self, v):
        return check_float(self.key, v)


class BoolRealTimeConfigEntry(RealTimeConfigEntry[bool]):

    def deserialize_value(self, v):
        return check_bool(self.key, v)


class RealTimeConfigManager(Protocol):
    ...


@dataclass
class _Config:
    host: str = "localhost"
    port: int = 2379
    module_name: str = "realtime_configs"


def get_event_name(key):
    return f"EVENT_REALTIME_CONFIG_UPDATED[{key}]"


def _patch_etcd3_client():
    def _with_retry(f):
        return retry(wait_fixed=10000, retry_on_exception=lambda e: isinstance(e, ConnectionFailedError))(f)

    Etcd3Client.get = _with_retry(Etcd3Client.get)
    Etcd3Client.put = _with_retry(Etcd3Client.put)
    Etcd3Client.put_if_not_exists = _with_retry(Etcd3Client.put_if_not_exists)


@bean(cfg=("realtime-config.etcd", _Config, _Config()))
class ETCDRealTimeConfigManagerImpl(RealTimeConfigManager):
    config_service: ConfigService
    events: Events

    def init(self, **kwargs):
        self._client = etcd3.client(host=self.cfg.host, port=self.cfg.port)
        _patch_etcd3_client()
        self._bind_entries()

    def etcd(self) -> Etcd3Client:
        return self._client

    def _bind_entries(self):
        inj = injector()
        for name, obj in vars(__import__(self.cfg.module_name)).items():
            if isinstance(obj, type) and issubclass(obj, RealTimeConfigEntry) and obj != RealTimeConfigEntry:
                entry = inj.inject(obj)
                setattr(self, camelcase.camel2snake(name), entry)
                self._bind_entry(entry)

    def _compile_key(self, key: str) -> str:
        return f"/{self.config_service.app_name()}/{key}"

    def _bind_entry(self, e: RealTimeConfigEntry):
        if not e.key:
            e.key = str(type(e))
        server_key = self._compile_key(e.key)
        value_from_server, metadata = self._client.get(server_key)
        if value_from_server is None:
            self._client.put_if_not_exists(server_key, pickle.dumps(e.value))
        else:
            e.value = e.deserialize_value(pickle.loads(value_from_server))

        if e.watched:
            def on_updated(external_value_response: WatchResponse):
                event = next(filter(lambda evnt: isinstance(evnt, PutEvent), external_value_response.events), None)
                if event:
                    old_value = e.value
                    e.value = e.deserialize_value(event.value)
                    self.events.notify(get_event_name(e.key), old_value=old_value, entry=e)

            self._client.add_watch_callback(server_key, on_updated)
