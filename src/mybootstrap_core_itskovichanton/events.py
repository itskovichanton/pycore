"""Глобальная шина событий приложения и флаг штатного завершения процесса."""
from threading import Event

from event_bus import EventBus

event_bus = EventBus()
exit_signal = Event()
