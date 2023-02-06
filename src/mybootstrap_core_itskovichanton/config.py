import os
import yaml
from benedict import benedict
from dacite import from_dict
from dataclasses import dataclass
from src.mybootstrap_ioc_itskovichanton.ioc import bean
from src.mybootstrap_ioc_itskovichanton.utils import create_benedict
from typing import Protocol, Optional


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


class ConfigService(Protocol):

    def __init__(self):
        self.config = None

    def get_config(self) -> Config:
        pass

    def dir(self, *args) -> str:
        """App directory"""

    def app_name(self) -> str:
        """A Flyer can fly"""


class ConfigLoaderService(Protocol):
    def load(self) -> Config:
        """Loads config instance"""


@bean(filename=("config-file", str, "config.yml"), encoding=("config-file.encoding", str, "utf-8"))
class YamlConfigLoaderServiceImpl(ConfigLoaderService):

    def load(self) -> Config:
        with open(self.filename, encoding=self.encoding) as f:
            settings: dict = yaml.load(f, Loader=yaml.FullLoader)
            profile = self._context.profile
            profile_settings = settings[profile]
            for k, v in profile_settings.items():
                s = settings.get(k)
                if s:
                    s.update(v)
                else:
                    settings[k] = v
            r = from_dict(data_class=Config, data=settings)
            settings.pop(profile)
            r.settings = create_benedict(settings)
            r.profile = profile

        return r


@bean(workdir=("workdir", str, ""))
class ConfigServiceImpl(ConfigService):
    config_loader: ConfigLoaderService

    def init(self, **kwargs):
        self.config = self.config_loader.load()
        self.dir()

    def get_config(self) -> Config:
        return self.config

    def app_name(self) -> str:
        return self.config.full_name()

    def dir(self, *args) -> str:
        r = os.path.join(self.workdir, self.config.app.full_name(), "work", self.config.profile, *args)
        os.makedirs(r, exist_ok=True)
        return r
