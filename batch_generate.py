import subprocess
import sys
from pathlib import Path

from _constants import FFMPEG_PATH
from _exceptions import CsvParseError
from _types import TaskResult
from api_client import AgnesClient
import cli
import config as config_module
import reader
import reporter
import runner
import validator


def _add_subtitles(tasks: list, concat_path: str, output_dir: str) -> None:
    """从任务的subtitle字段生成SRT并混入视频"""
    srt = Path(output_dir) / "_subtitles.srt"
    time_cursor = 0.0
    with open(srt, "w", encoding="utf-8") as f:
        for i, t in enumerate(tasks):
            if not t.subtitle:
                time_cursor += (t.num_frames or 81) / (t.frame_rate or 24)
                continue
            dur = (t.num_frames or 81) / (t.frame_rate or 24)
            end = time_cursor + dur
            h1, m1, s1 = int(time_cursor//3600), int((time_cursor%3600)//60), time_cursor%60
            h2, m2, s2 = int(end//3600), int((end%3600)//60), end%60
            f.write(f"{i+1}\n{h1:02d}:{m1:02d}:{s1:06.3f} --> {h2:02d}:{m2:02d}:{s2:06.3f}\n{t.subtitle}\n\n".replace(".",","))
            time_cursor = end

    if not srt.exists() or srt.stat().st_size == 0:
        srt.unlink(missing_ok=True)
        return

    out = Path(concat_path)
    tmp = out.with_suffix(".tmp.mp4")
    try:
        subprocess.run([
            FFMPEG_PATH, "-y", "-i", str(out), "-i", str(srt),
            "-c", "copy", "-c:s", "mov_text", "-metadata:s:s:0", "language=chi",
            str(tmp),
        ], check=True, capture_output=True, encoding="utf-8", errors="replace")
        tmp.replace(out)
    except Exception:
        pass
    srt.unlink(missing_ok=True)


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

    # Generate subtitles and mux into final video
    if args.concat:
        concat_path = str(Path(config.output_dir) / args.concat_name)
        _add_subtitles(tasks, concat_path, config.output_dir)
        if Path(concat_path).exists():
            logger.info(f"字幕已混入: {concat_path}")

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