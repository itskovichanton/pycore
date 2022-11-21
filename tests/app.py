
from src.bootstrapcore_itskovichanton.alerts import AlertService, alert_on_fail, Alert
from src.bootstrapcore_itskovichanton.app import Application
from src.bootstrapcore_itskovichanton.config import ConfigService


class TestCoreApp(Application):

    def __init__(self, config_service: ConfigService, alert_service: AlertService):
        super().__init__(config_service)
        self.alert_service = alert_service

    def run(self):
        print(self.config_service.app_name())

    async def async_run(self):
        print(self.config_service.app_name())
        # self.http_controller.start()
        # print(await self.do_stuff_with_errors())
        await self.alert_service.send(Alert(level=1, message="Test", subject="Error happened", byEmail=False))
        # uvicorn.run("main:app", reload=True, workers=4)

    # @wrapper()
    def do_stuff_with_errors1(self):
        return "Hello"

    @alert_on_fail
    async def do_stuff_with_errors(self):
        return f"{1 / 0}"
