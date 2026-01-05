from fastapi import FastAPI
from src.mybootstrap_ioc_itskovichanton.ioc import bean
from src.mybootstrap_ioc_itskovichanton.utils import default_dataclass_field
from src.mybootstrap_mvc_fastapi_itskovichanton.presenters import JSONResultPresenterImpl
from src.mybootstrap_mvc_itskovichanton.result_presenter import ResultPresenter
from starlette.requests import Request

from src.mybootstrap_core_itskovichanton.realtimeconfig.controller import EtcdController


@bean
class RealtimeConfigFastAPISupport:
    controller: EtcdController
    result_presenter: ResultPresenter = default_dataclass_field(JSONResultPresenterImpl())

    def mount(self, fast_api: FastAPI):
        @fast_api.get("/etcd/list")
        async def get_etcds(request: Request):
            result = await self.controller.get_etcds()
            return self.result_presenter.present(result)
