import random
import time
from dataclasses import dataclass

import uvicorn
from fastapi import FastAPI
from retrying import retry
from src.mybootstrap_ioc_itskovichanton.config import ConfigService
from src.mybootstrap_ioc_itskovichanton.ioc import bean
from src.mybootstrap_mvc_fastapi_itskovichanton.middleware_logging import HTTPLoggingMiddleware
from src.mybootstrap_mvc_itskovichanton.exceptions import CoreException
from starlette.middleware.cors import CORSMiddleware

from src.mybootstrap_core_itskovichanton.alerts import AlertService, alert_on_fail
from src.mybootstrap_core_itskovichanton.app import Application
from src.mybootstrap_core_itskovichanton.logger import LoggerService, log
from src.mybootstrap_core_itskovichanton.metrics_export import MetricsExporter
from src.mybootstrap_core_itskovichanton.realtime_config import RealTimeConfigManager
from src.mybootstrap_core_itskovichanton.realtimeconfig.support import RealtimeConfigFastAPISupport

from src.mybootstrap_core_itskovichanton.redis_service import RedisService
from src.mybootstrap_core_itskovichanton.shell import ShellService
from test_ioc import AbstractService, MyBean
from test_etcd import MyService


@dataclass
class MyValue1:
    a: str = "a"
    b: int = 10


@dataclass
class MyValue2:
    v: MyValue1
    f1: str = "def"
    f2: int = 10


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
    me: MetricsExporter
    rds: RedisService
    real_time_config: RealTimeConfigManager
    rt_fapi_support: RealtimeConfigFastAPISupport
    my_service: MyService

    def init(self, **kwargs):
        self.logger = self.logger_service.get_file_logger("tests")

    @retry(wait_fixed=10000)
    def test1(self):
        print(self.config_service.app_name())
        raise CoreException("oops")

    def run(self):
        self.test_redis()
        # self.test1()
        print(self.config_service.app_name())
        rds = self.rds.get()
        self.fast_api = self.init_fast_api()
        uvicorn.run(self.fast_api, port=3333, host="localhost")
        # self.raise_err()
        i = 0
        # while True:
        #     self.do_stuff_with_errors(1, 2, c=i)
        #     i += 1
        #     time.sleep(0.100)

        self.alert_service.get_interceptors().append(ignore_some_errors)
        # do_other_stuff_with_errors(1, 2, 3, 4)

    @alert_on_fail
    def raise_err(self):
        print(1 / 0)

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

    @log(_logger="tests", _suppress_fail=True)
    def do_stuff_with_errors(self, a, b, c=4):
        if random.randint(0, 10) < 5:
            raise CoreException(message="Тест-Ошибка!")
        print("Hello")
        return "OK"

    def test_redis(self):
        kv = self.rds.make_map(hname="stats", value_class=MyValue2)
        kv.set("k1", MyValue2(v=MyValue1(a="xxxxx", b=100)))
        kv.set("k2", MyValue2(v=MyValue1(a="aaa", b=-2)))
        kv.set("k3", MyValue2(v=MyValue1(a="bbb", b=100), f1="f1", f2=30))

        v1 = kv.get("k1")
        v2 = kv.get("k2")
        v3 = kv.get("k3")

        print(v1, v2, v3)

    def init_fast_api(self) -> FastAPI:
        r = FastAPI(title='cherkizon', debug=False)
        self.rt_fapi_support.mount(r)
        # self.healthcheck_support.mount(r)
        r.add_middleware(HTTPLoggingMiddleware, encoding="utf-8", logger=self.logger_service.get_file_logger("http"))
        r.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            # Здесь можно указать разрешенные источники, например ["http://localhost", "http://localhost:3000"]
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        return r
