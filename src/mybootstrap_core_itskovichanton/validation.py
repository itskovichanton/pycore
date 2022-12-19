from src.mybootstrap_mvc_itskovichanton.exceptions import CoreException, ERR_REASON_VALIDATION

VALIDATION_REASON_EMPTY = "EMPTY"
VALIDATION_REASON_INVALID_INT = "INVALID_INT"
VALIDATION_REASON_INVALID_FLOAT = "INVALID_FLOAT"
VALIDATION_REASON_UNEXPECTABLE = "UNEXPECTABLE"


# TODO: реализуй
# VALIDATION_REASON_INVALID_LEN = "INVALID_LENGTH"
# VALIDATION_REASON_INVALID_EMAIL = "INVALID_EMAIL"
# VALIDATION_REASON_BOOL = "INVALID_BOOLEAN"


class ValidationException(CoreException):
    def __init__(self, message: str, param: str, invalid_value,
                 validation_reason: str = VALIDATION_REASON_UNEXPECTABLE, cause: BaseException = None):
        super().__init__(message, reason=ERR_REASON_VALIDATION, cause=cause)
        self.param = param
        self.validation_reason = validation_reason
        self.invalidValue = invalid_value


def check_int(param: str, value, message="Некорректное int-значение") -> int:
    try:
        return int(value)
    except Exception as e:
        raise ValidationException(message=message,
                                  invalid_value=value, param=param,
                                  validation_reason=VALIDATION_REASON_INVALID_INT, cause=e)


def check_float(param: str, value, message="Некорректное float-значение") -> float:
    try:
        return float(value)
    except Exception as e:
        raise ValidationException(message=message, invalid_value=value, param=param,
                                  validation_reason=VALIDATION_REASON_INVALID_FLOAT, cause=e)


def check_not_empty(param: str, value, message: str = "Параметр не может содержать пустое значение"):
    if not value:
        raise ValidationException(message=message, invalid_value=value, param=param,
                                  validation_reason=VALIDATION_REASON_EMPTY)
    return value
