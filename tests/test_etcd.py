from time import sleep

from paprika import threaded
from prometheus_client import Counter
from src.mybootstrap_ioc_itskovichanton.config import ConfigService
from src.mybootstrap_ioc_itskovichanton.ioc import bean

from realtime_configs import MyNameRealTimeConfigEntry, PrintMyNameTimeIntervalRealTimeConfigEntry
from src.mybootstrap_core_itskovichanton.logger import LoggerService


@bean
class MyService:
    logger_service: LoggerService
    config_service: ConfigService
    my_name: MyNameRealTimeConfigEntry
    interval: PrintMyNameTimeIntervalRealTimeConfigEntry

    def init(self, **kwargs):
        self._logger = self.logger_service.get_graylog_logger("myservice")
        self._start_test()

    @threaded
    def _start_test(self):
        c = Counter('my_counter', 'Description of counter')
        while True:
            print(self.my_name.value)
            self._logger.error({"v": self.my_name.value, "app": self.config_service.app_name()})
            self._logger.error("hello")
            c.inc(1)
            sleep(self.interval.value)
