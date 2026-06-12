import argparse
from pathlib import Path

from _types import AppConfig


def load_config(args: argparse.Namespace) -> AppConfig:
    key_path = Path(args.key)
    if not key_path.exists():
        raise FileNotFoundError(f"API Key 文件不存在: {key_path}")

    lines = key_path.read_text(encoding="utf-8").strip().splitlines()
    api_key = lines[0].strip() if lines else ""

    return AppConfig(
        api_key=api_key,
        base_url="https://apihub.agnes-ai.com",
        csv_path=args.csv,
        output_dir=args.output,
        poll_interval=args.interval,
        max_retries=args.max_retries,
        log_file=args.log,
    )