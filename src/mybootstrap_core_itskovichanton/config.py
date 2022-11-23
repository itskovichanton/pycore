import os
from dataclasses import dataclass
from typing import Protocol, Optional

import yaml
from benedict import benedict
from dacite import from_dict

from src.mybootstrap_core_itskovichanton.ioc import bean
from src.mybootstrap_core_itskovichanton.utils import create_benedict


class ConfigService(Protocol):

    def __init__(self):
        self.config = None

    def dir(self) -> str:
        """App directory"""

    def app_name(self) -> str:
        """A Flyer can fly"""


@dataclass
class App:
    name: str
    version: str

    def full_name(self):
        return f"{self.name}-{self.version}"


@dataclass
class Config:
    app: App
    settings: Optional[benedict]
    profile: Optional[str]

    def full_name(self):
        return f"{self.app.full_name()}-[{self.profile}]"

    def is_prod(self):
        return self.profile == "prod"


class ConfigLoaderService(Protocol):
    def load(self) -> Config:
        """Loads config instance"""


@bean(filename=("config-file", str, "config.yml"))
class YamlConfigLoaderServiceImpl(ConfigLoaderService):

    def load(self) -> Config:
        with open(self.filename) as f:
            settings: dict = yaml.load(f, Loader=yaml.FullLoader)
            profile = self._context.profile
            profile_settings = settings[profile]
            for k, v in profile_settings.items():
                settings[k] = v
            r = from_dict(data_class=Config, data=settings)
            settings.pop(profile)
            r.settings = create_benedict(settings)
            r.profile = profile

        return r


@bean
class ConfigServiceImpl(ConfigService):
    config_loader: ConfigLoaderService

    def init(self, **kwargs):
        self.config = self.config_loader.load()
        self.dir()

    def app_name(self) -> str:
        return self.config.full_name()

    def dir(self) -> str:
        r = os.path.join(self.config.app.full_name(), "work", self.config.profile)
        os.makedirs(r, exist_ok=True)
        return r

    # def on_dir(self, *args) -> str:
    #     r = os.path.join(self.dir(), list(args))
    #     os.makedirs(r, exist_ok=True)
    #     return r
