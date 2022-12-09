from src.mybootstrap_ioc_itskovichanton.ioc import bean

from src.mybootstrap_core_itskovichanton.alerts import AlertService, alert_on_fail, Alert
from src.mybootstrap_core_itskovichanton.app import Application
from src.mybootstrap_core_itskovichanton.config import ConfigService
from src.mybootstrap_core_itskovichanton.logger import LoggerService
from tests.test_ioc import AbstractService, MyBean


@bean(no_polymorph=True)
class TestCoreApp(Application):
    service: AbstractService
    alert_service: AlertService
    config_service: ConfigService
    logger_service: LoggerService
    mybean: MyBean

    def run(self):
        print(self.config_service.app_name())

    async def async_run(self):
        self.logger_service.get_file_logger("my").info({"a": 1})
        self.service.do_smth()
        print(self.config_service.app_name())
        print(self.mybean.info())
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
