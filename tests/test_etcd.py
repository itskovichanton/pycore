from time import sleep

from paprika import threaded
from src.mybootstrap_ioc_itskovichanton.ioc import bean

from realtime_configs import MyNameRealTimeConfigEntry, PrintMyNameTimeIntervalRealTimeConfigEntry


@bean
class MyService:
    my_name: MyNameRealTimeConfigEntry
    interval: PrintMyNameTimeIntervalRealTimeConfigEntry

    def init(self, **kwargs):
        self._start_test()

    @threaded
    def _start_test(self):
        while True:
            print(self.my_name.value)
            sleep(self.interval.value)
