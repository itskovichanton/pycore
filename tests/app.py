from src.mybootstrap_ioc_itskovichanton.ioc import bean
from src.mybootstrap_mvc_itskovichanton.exceptions import CoreException

from src.mybootstrap_core_itskovichanton.alerts import AlertService
from src.mybootstrap_core_itskovichanton.app import Application
from src.mybootstrap_core_itskovichanton.config import ConfigService
from src.mybootstrap_core_itskovichanton.logger import LoggerService, log
from src.mybootstrap_core_itskovichanton.shell import ShellService
from test_ioc import AbstractService, MyBean


#
# @log_decorator
# def do_other_stuff_with_errors(a, b, c, d):
#     raise CoreException(message="don't tell me anything", reason="ignored_reason")


def ignore_some_errors(e: BaseException) -> BaseException:
    if isinstance(e, CoreException):
        if e.reason == "ignored_reason":
            return None
    return e


@bean(no_polymorph=True)
class TestCoreApp(Application):
    service: AbstractService
    alert_service: AlertService
    config_service: ConfigService
    logger_service: LoggerService
    shell_service: ShellService
    mybean: MyBean

    def init(self, **kwargs):
        self.logger = self.logger_service.get_file_logger("tests")

    def run(self):
        print(self.config_service.app_name())
        self.do_stuff_with_errors(1, 2, c=3)
        self.alert_service.get_interceptors().append(ignore_some_errors)
        # do_other_stuff_with_errors(1, 2, 3, 4)

    #  def _run(self):
    #     self.alert_service.get_interceptors().append(ignore_some_errors)
    #     await self.do_other_stuff_with_errors()
    #     self.cmd = os.path.join(self.config_service.dir("cmd"), "testbash.sh")
    #     print(self.shell_service.execute(self.cmd, "hello"))
    #     await self.do_stuff_with_errors()
    #     self.logger_service.get_file_logger("my").info({"a": 1})
    #     self.service.do_smth()
    #     print(self.config_service.app_name())
    #     print(self.mybean.info())
    #     # self.http_controller.start()
    #     # print(await self.do_stuff_with_errors())
    #     await self.alert_service.send(Alert(level=1, message="Test", subject="Error happened", byEmail=False))
    #     # uvicorn.run("main:app", reload=True, workers=4)

    # @wrapper()
    def do_stuff_with_errors1(self):
        return "Hello"

    @log(_logger="tests", _desc=lambda args, kwargs: f"do stuff with {kwargs['c']}, 1st arg = {args[0]}")
    def do_stuff_with_errors(self, a, b, c=4):
        return self.shell_service.execute(self.cmd, "err")
