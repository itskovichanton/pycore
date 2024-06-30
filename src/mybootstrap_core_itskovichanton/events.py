from typing import Protocol

from event_bus import EventBus

from src.mybootstrap_core_itskovichanton.di import injector
from src.mybootstrap_ioc_itskovichanton.ioc import bean


class Events(Protocol):

    def notify(self, event: str, *args, **kwargs):
        ...


@bean
class EventsImpl(Events):
    event_bus: EventBus = None

    def notify(self, event: str, *args, **kwargs):
        self.event_bus.emit(event, *args, **kwargs)


events = injector().inject(Events)


def emit(event_name, threads=True):
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            events.notify(event_name, result, threads=threads)
            return result

        return wrapper

    return decorator
