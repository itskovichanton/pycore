from typing import Protocol


class Application(Protocol):

    async def async_run(self):
        """Run in async mode"""

    def run(self):
        """Run sync"""
