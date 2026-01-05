from typing import Any

from src.mybootstrap_ioc_itskovichanton.ioc import bean
from src.mybootstrap_mvc_itskovichanton.pipeline import Action, ActionRunner
from src.mybootstrap_pyauth_itskovichanton.frontend.controller import GetUserAction

from src.mybootstrap_core_itskovichanton.realtime_config import RealTimeConfigManager


@bean
class ListEtcdsAction(Action):
    rtcfg_mgr: RealTimeConfigManager

    def run(self, p=None) -> Any:
        b = self.rtcfg_mgr.get_bindings()
        b = [b[key] for key in sorted(b.keys())]
        return {"key_prefix": self.rtcfg_mgr.get_key_prefix(),
                "data": [
                    {"value_type": type(p.get_value_type()),
                     "key": p.key,
                     "description": p.description,
                     "watched": p.watched,
                     "value": p.value,
                     "category": p.category,
                     }
                    for p in b]}


@bean
class EtcdController:
    get_etcds_action: ListEtcdsAction
    action_runner: ActionRunner
    get_user_action: GetUserAction

    async def get_etcds(self):
        return await self.action_runner.run(self.get_etcds_action)
