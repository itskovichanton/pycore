from dateutil.utils import today
from src.mybootstrap_ioc_itskovichanton.ioc import bean

from common import User
from src.mybootstrap_core_itskovichanton.realtime_config import RealTimeConfigEntry, IntRealTimeConfigEntry


# Group author

@bean
class MyAgeRealTimeConfigEntry(IntRealTimeConfigEntry):
    key = "my_age"
    description = "мой возраст"
    value = 4
    watched = "False"


@bean
class PrintMyNameTimeIntervalRealTimeConfigEntry(IntRealTimeConfigEntry):
    key = "sync_services_time_interval"
    description = "интервал задержки между выводом строк (сек)"
    value = 5
    watched = "False"


@bean
class MyNameRealTimeConfigEntry(RealTimeConfigEntry[str]):
    key = "my_name"
    description = "мое имя"
    value = "Антон"
    watched = False


@bean
class MyUserRealTimeConfigEntry(RealTimeConfigEntry[User]):
    key = "my_user"
    description = "текущий пользователь"
    value = User(age=30, name="Антон Ицкович", birthdate=today())
    watched = False

#
# @bean
# class MyBirthdateRealTimeConfigEntry(RealTimeConfigEntry[str]):
#     key = "my_birthdate"
#     description = "мой др"
#     value = "04.12.1998"
#     watched = "False"
#
#
# # Group sync
#
# @bean
# class IgnoreSyncServicesRealTimeConfigEntry(RealTimeConfigEntry[str]):
#     key = "ignore_sync_services"
#     description = "игнорировать синк сервисов из gitlab"
#     value = "False"
#     watched = "False"
#
#
# @bean
# class MinIntervalRealTimeConfigEntry(RealTimeConfigEntry[str]):
#     key = "min_interval"
#     description = "минимальный промежуток времени в течение которого сервис не надо обновлять"
#     value = "10m"
#     watched = "False"
