from typing import Protocol

from config import ConfigService, Config


class Application(Protocol):

    def __init__(self, config_service: ConfigService):
        self.config_service = config_service

    def run(self):
        """Abstract application"""
