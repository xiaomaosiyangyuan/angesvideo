import argparse

from _constants import DEFAULT_KEY_FILE, DEFAULT_LOG_FILE, DEFAULT_MAX_RETRIES, DEFAULT_OUTPUT_DIR, DEFAULT_POLL_INTERVAL


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Agnes Video V2.0 批量视频生成工具",
    )
    parser.add_argument("--csv", required=True, type=str, help="任务 CSV 文件路径")
    parser.add_argument("--output", "-o", type=str, default=DEFAULT_OUTPUT_DIR, help="视频下载目录")
    parser.add_argument("--key", "-k", type=str, default=DEFAULT_KEY_FILE, help="API Key 文件路径")
    parser.add_argument("--interval", type=int, default=DEFAULT_POLL_INTERVAL, help="轮询间隔（秒）")
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES, help="单任务最大重试次数")
    parser.add_argument("--log", type=str, default=DEFAULT_LOG_FILE, help="日志文件路径")
    parser.add_argument("--concat", action="store_true", help="生成完成后自动拼接所有视频")
    parser.add_argument("--concat-name", type=str, default="final_cut.mp4", help="拼接输出文件名")
    return parser.parse_args(argv)