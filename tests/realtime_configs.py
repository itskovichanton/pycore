from dateutil.utils import today
from src.mybootstrap_ioc_itskovichanton.ioc import bean

from common import User
from src.mybootstrap_core_itskovichanton.realtime_config import RealTimeConfigEntry, IntRealTimeConfigEntry


@bean
class MyAgeRealTimeConfigEntry(IntRealTimeConfigEntry):
    key = "my_age"
    description = "мой возраст"
    value = 4
    value_type = int
    category = "cat3"
    watched = False


@bean
class PrintMyNameTimeIntervalRealTimeConfigEntry(IntRealTimeConfigEntry):
    key = "sync_services_time_interval"
    description = "интервал задержки между выводом строк (сек)"
    value = 5
    value_type = int
    category = "cat2"
    watched = True


@bean
class MyNameRealTimeConfigEntry(RealTimeConfigEntry[str]):
    key = "my_name"
    description = "мое имя"
    category = "cat1"
    value_type = str
    value = "Антон"
    watched = False


@bean
class MyUserRealTimeConfigEntry(RealTimeConfigEntry[User]):
    key = "my_user"
    category = "cat1"
    value_type = User
    description = "текущий пользователь"
    value = User(age=30, name="Антон Ицкович", birthdate=today())
    watched = False
