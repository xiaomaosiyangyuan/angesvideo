import pytest
from pathlib import Path

from config import load_config
from cli import parse_args


class TestLoadConfig:
    def test_normal_key_file(self) -> None:
        key_path = Path(__file__).parent / "fixtures" / "key.txt"
        args = parse_args(["--csv", "tasks.csv", "--key", str(key_path)])
        cfg = load_config(args)
        assert cfg.api_key == "sk-test-key-for-testing"
        assert cfg.csv_path == "tasks.csv"
        assert cfg.base_url == "https://apihub.agnes-ai.com"

    def test_key_file_not_found(self) -> None:
        args = parse_args(["--csv", "tasks.csv", "--key", "/nonexistent/key.txt"])
        with pytest.raises(FileNotFoundError):
            load_config(args)