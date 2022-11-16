from alerts import AlertService, Alert
from app import Application
from config import ConfigService


class TestCoreApplication(Application):

    def __init__(self, config_service: ConfigService, alert_service: AlertService):
        super().__init__(config_service)
        self.alert_service = alert_service

    async def run(self):
        print(self.config_service.app_name())
        await self.alert_service.send(Alert(level=1, message="Test", subject="Error happened", byEmail=False))
