"""Контракт точки входа приложения: sync ``run`` и async ``async_run``."""
from typing import Protocol


class Application(Protocol):
    """Корневой bean сервиса: IoC создаёт его и вызывает ``run()`` из ``main``."""

    async def async_run(self):
        """Run in async mode"""

    def run(self):
        """Run sync"""
