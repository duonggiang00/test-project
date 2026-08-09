from collections.abc import Mapping


class AppException(Exception):
    def __init__(
        self,
        error_code: str,
        status_code: int = 400,
        message: str | None = None,
        detail: str | None = None,
        details: object | None = None,
        headers: Mapping[str, str] | None = None,
    ):
        super().__init__(error_code)
        self.error_code = error_code
        self.status_code = status_code
        self.message = message
        self.detail = detail
        self.details = {} if details is None else details
        self.headers = headers
