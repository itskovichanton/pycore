from fastapi import FastAPI
from src.mybootstrap_ioc_itskovichanton.ioc import bean
from src.mybootstrap_ioc_itskovichanton.utils import default_dataclass_field
from src.mybootstrap_mvc_fastapi_itskovichanton.presenters import JSONResultPresenterImpl
from src.mybootstrap_mvc_itskovichanton.result_presenter import ResultPresenter
from src.mybootstrap_pyauth_itskovichanton.frontend.utils import get_caller_from_request
from starlette.requests import Request

from src.mybootstrap_core_itskovichanton.info.frontend.controller import InfoController


@bean
class InfoFastAPISupport:
    controller: InfoController
    result_presenter_json: ResultPresenter = default_dataclass_field(JSONResultPresenterImpl())

    def mount(self, fast_api: FastAPI):
        @fast_api.get("/info")
        async def healthcheck(request: Request):
            return self.result_presenter_json.present(
                await self.controller.get_info(caller=get_caller_from_request(request))
            )
