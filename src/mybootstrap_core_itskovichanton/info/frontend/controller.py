from typing import Any

from greenletio import async_, await_
from src.mybootstrap_ioc_itskovichanton.ioc import bean
from src.mybootstrap_mvc_itskovichanton.pipeline import Action, ActionRunner
from src.mybootstrap_pyauth_itskovichanton.entities import Caller

from src.mybootstrap_core_itskovichanton.info.backend.info import GetInfoUsecase


@bean
class GetInfoAction(Action):
    info_uc: GetInfoUsecase

    def run(self, params: Any = None) -> Any:
        return self.info_uc.info()


@bean
class InfoController:
    get_info_action: GetInfoAction
    action_runner: ActionRunner

    @async_
    def get_info(self, caller: Caller):
        return await_(self.action_runner.run(self.get_info_action, call=caller))
