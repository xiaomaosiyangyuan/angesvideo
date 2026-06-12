import pytest

from cli import parse_args


class TestParseArgs:
    def test_full_args(self) -> None:
        ns = parse_args(["--csv", "tasks.csv", "-o", "./vid", "-k", "./mykey.txt",
                         "--interval", "10", "--max-retries", "5", "--log", "./my.log"])
        assert ns.csv == "tasks.csv"
        assert ns.output == "./vid"
        assert ns.key == "./mykey.txt"
        assert ns.interval == 10
        assert ns.max_retries == 5
        assert ns.log == "./my.log"

    def test_minimal_args(self) -> None:
        ns = parse_args(["--csv", "tasks.csv"])
        assert ns.csv == "tasks.csv"
        assert ns.output == "./output"
        assert ns.key == "./key.txt"
        assert ns.interval == 5
        assert ns.max_retries == 3
        assert ns.log == "./batch.log"

    def test_missing_csv_raises_system_exit(self) -> None:
        with pytest.raises(SystemExit) as exc:
            parse_args([])
        assert exc.value.code == 2

    def test_invalid_interval_type(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--csv", "t.csv", "--interval", "abc"])