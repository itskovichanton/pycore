import os
import pickle
import threading

import dacite
from etcd3.events import PutEvent
from etcd3.watch import WatchResponse

from src.mybootstrap_core_itskovichanton.events import Events
from src.mybootstrap_core_itskovichanton.validation import check_int, check_float, check_bool

os.putenv("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
from dataclasses import dataclass
from typing import Protocol, TypeVar, Generic, Any

import etcd3
from src.mybootstrap_ioc_itskovichanton.config import ConfigService
from src.mybootstrap_ioc_itskovichanton.ioc import bean

T = TypeVar('T')


def default_deserializer(value_class, value_dict):
    return dacite.from_dict(data_class=value_class, data=value_dict,
                            config=dacite.Config(strict=False, check_types=False))


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

    def bind(self, e: RealTimeConfigEntry):
        ...


@dataclass
class _Config:
    host: str = "localhost"
    port: int = 2379
    enabled: bool = True


def get_event_name(key):
    return f"EVENT_REALTIME_CONFIG_UPDATED[{key}]"


@bean(cfg=("realtime-config.etcd", _Config, _Config()))
class ETCDRealTimeConfigManagerImpl(RealTimeConfigManager):
    config_service: ConfigService
    events: Events

    def init(self, **kwargs):
        if self.cfg.enabled:
            self.client = etcd3.client(host=self.cfg.host, port=self.cfg.port)

    def _compile_key(self, key: str) -> str:
        return f"/{self.config_service.app_name()}/{key}"

    def bind(self, e: RealTimeConfigEntry):
        if not e.key:
            e.key = str(type(e))
        server_key = self._compile_key(e.key)
        value_from_server, metadata = self.client.get(server_key)
        if value_from_server is None:
            self.client.put_if_not_exists(server_key, pickle.dumps(e.value))
        else:
            e.value = e.deserialize_value(pickle.loads(value_from_server))

        if e.watched:
            def on_updated(external_value_response: WatchResponse):
                event = next(filter(lambda evnt: isinstance(evnt, PutEvent), external_value_response.events), None)
                if event:
                    old_value = e.value
                    e.value = e.deserialize_value(event.value)
                    self.events.notify(get_event_name(e.key), old_value=old_value, entry=e)

            self.client.add_watch_callback(server_key, on_updated)
