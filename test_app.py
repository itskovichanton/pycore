from alerts import AlertService, alert_on_fail
from app import Application
from config import ConfigService


class TestCoreApplication(Application):

    def __init__(self, config_service: ConfigService, alert_service: AlertService):
        super().__init__(config_service)
        self.alert_service = alert_service

    async def run(self):
        print(self.config_service.app_name())
        print(await self.do_stuff_with_errors())
        # await self.alert_service.send(Alert(level=1, message="Test", subject="Error happened", byEmail=False))

    # @wrapper()
    def do_stuff_with_errors1(self):
        return "Hello"

    @alert_on_fail
    async def do_stuff_with_errors(self):
        return f"{1/0}"
