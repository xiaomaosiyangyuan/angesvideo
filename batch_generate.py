import sys

from _exceptions import CsvParseError
from _types import TaskResult
from api_client import AgnesClient
import cli
import config as config_module
import reader
import reporter
import runner
import validator


def main() -> None:
    args = cli.parse_args()

    try:
        config = config_module.load_config(args)
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    logger = reporter.setup_logger(config.log_file)
    logger.info("=" * 50)
    logger.info("Agnes Video V2.0 批量视频生成工具")
    logger.info(f"CSV: {config.csv_path}")
    logger.info(f"输出: {config.output_dir}")
    logger.info("=" * 50)

    try:
        tasks = reader.read_tasks(config.csv_path)
        logger.info(f"读取到 {len(tasks)} 条任务")
    except (FileNotFoundError, CsvParseError) as e:
        logger.error(f"读取 CSV 失败: {e}")
        sys.exit(1)

    all_errors: list[tuple[int, list[str]]] = []
    for i, task in enumerate(tasks, start=1):
        errs = validator.validate(task)
        if errs:
            all_errors.append((i, errs))

    if all_errors:
        logger.error("参数校验失败:")
        for row_idx, errs in all_errors:
            for err in errs:
                logger.error(f"  第 {row_idx} 行: {err}")
        sys.exit(1)

    logger.info("所有任务参数校验通过")

    client = AgnesClient(api_key=config.api_key, base_url=config.base_url)

    logger.info("开始批量生成...")

    def progress_callback(current: int, total: int, result: TaskResult) -> None:
        status_icon = {
            "success": "✓",
            "failed": "✗",
            "skipped": "→",
            "interrupted": "⚠",
        }.get(result.status, "?")
        msg = (
            f"[{current}/{total}] {status_icon} 第 {result.row_index} 行 "
            f"- {result.status}"
        )
        if result.output_path:
            msg += f" - {result.output_path}"
        if result.error_message:
            msg += f" - {result.error_message}"
        logger.info(msg)

    results = runner.run_batch(
        tasks, client, config,
        progress_callback=progress_callback,
        concat=args.concat,
        concat_name=args.concat_name,
        parallel=args.parallel,
    )

    csv_path = reporter.write_results_csv(results, config.output_dir)
    logger.info(f"结果报告已保存: {csv_path}")

    success_count = sum(1 for r in results if r.status == "success")
    failed_count = sum(1 for r in results if r.status == "failed")
    skipped_count = sum(1 for r in results if r.status in ("skipped", "interrupted"))
    logger.info("=" * 50)
    logger.info(f"全部完成: 成功 {success_count} / 失败 {failed_count} / 跳过 {skipped_count}")
    logger.info("=" * 50)

    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()