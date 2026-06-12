class CsvParseError(ValueError):
    def __init__(self, message: str, row_index: int | None = None) -> None:
        self.row_index = row_index
        super().__init__(message)


class ValidationError(ValueError):
    pass


class ApiError(Exception):
    def __init__(self, status_code: int, response_body: str, message: str = "") -> None:
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message or f"API 错误 {status_code}: {response_body[:200]}")


class NetworkError(Exception):
    pass