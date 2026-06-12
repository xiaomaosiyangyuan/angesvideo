
from _exceptions import CsvParseError, ValidationError, ApiError, NetworkError


class TestCsvParseError:
    def test_with_row_index(self) -> None:
        e = CsvParseError("parse error", row_index=5)
        assert e.row_index == 5
        assert "parse error" in str(e)

    def test_without_row_index(self) -> None:
        e = CsvParseError("generic error")
        assert e.row_index is None


class TestApiError:
    def test_default_message(self) -> None:
        e = ApiError(400, "bad request body")
        assert e.status_code == 400
        assert e.response_body == "bad request body"
        assert "400" in str(e)

    def test_custom_message(self) -> None:
        e = ApiError(401, "unauthorized", "Custom message")
        assert "Custom message" in str(e)


class TestNetworkError:
    def test_basic(self) -> None:
        e = NetworkError("connection timeout")
        assert "connection timeout" in str(e)


class TestValidationError:
    def test_basic(self) -> None:
        e = ValidationError("invalid params")
        assert "invalid params" in str(e)