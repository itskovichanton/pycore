from fastapi_utils import camelcase
from src.mybootstrap_ioc_itskovichanton.ioc import bean, injector

import realtime_configs
from src.mybootstrap_core_itskovichanton.realtime_config import RealTimeConfigManager, RealTimeConfigEntry


@bean
class RealTimeConfigs:
    cfg: RealTimeConfigManager

    def init(self, **kwargs):
        inj = injector()
        for name, obj in vars(realtime_configs).items():
            if isinstance(obj, type) and issubclass(obj, RealTimeConfigEntry) and obj != RealTimeConfigEntry:
                entry = inj.inject(obj)
                setattr(self, camelcase.camel2snake(name), entry)
                self.cfg.bind(entry)
