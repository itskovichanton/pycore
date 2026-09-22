from typing import Annotated, Optional
from datetime import date, datetime

from pydantic_utils import BeforeValidator, PlainSerializer, computed_field


def get_formatted_date_type(input_formats: list[str], output_format: str) -> type:
    def _parser(value: Optional[str]) -> Optional[date]:
        if value is None:
            return None
        for fmt in input_formats:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass
        return None

    def _serializer(value: Optional[date]) -> Optional[str]:
        if value is None:
            return None
        return value.strftime(value, output_format)

    return Annotated[
        Optional[date],
        BeforeValidator(_parser),
        PlainSerializer(_serializer, return_type=str | None)
    ]


def get_formatted_datetime_type(input_formats: list[str], output_format: str) -> type:
    def _parser(value: Optional[str]) -> Optional[datetime]:
        if value is None:
            return None
        for fmt in input_formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                pass
        return None

    def _serializer(value: Optional[datetime]) -> Optional[str]:
        if value is None:
            return None
        return value.strftime(value, output_format)

    return Annotated[
        Optional[datetime],
        BeforeValidator(_parser),
        PlainSerializer(_serializer, return_type=str | None)
    ]


@computed_field(return_type=None)
def none_field(_) -> None:
    return None
