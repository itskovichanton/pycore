from typing import Protocol

from config import ConfigService


class Application(Protocol):

    def __init__(self, config_service: ConfigService):
        self.config_service = config_service

    async def async_run(self):
        """Run in async mode"""

    def run(self):
        """Run sync"""
