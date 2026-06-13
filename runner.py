import logging
import signal
import subprocess
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from _constants import FFMPEG_PATH
from _exceptions import ApiError, NetworkError
from _types import AppConfig, TaskConfig, TaskResult, TaskStatus
from api_client import AgnesClient

ProgressCallback = Callable[[int, int, TaskResult], None]


def run_batch(
    tasks: list[TaskConfig],
    client: AgnesClient,
    config: AppConfig,
    progress_callback: ProgressCallback | None = None,
    concat: bool = False,
    concat_name: str = "final_cut.mp4",
    parallel: bool = False,
) -> list[TaskResult]:
    if parallel:
        return _run_parallel(tasks, client, config, progress_callback, concat, concat_name)
    return _run_serial(tasks, client, config, progress_callback, concat, concat_name)


# ── 串行模式（原有） ──────────────────────────────
def _run_serial(tasks, client, config, progress_callback, concat, concat_name):
    results: list[TaskResult] = []
    interrupted = False
    total = len(tasks)

    def handle_interrupt(signum, frame):
        nonlocal interrupted
        if not interrupted:
            print("\n收到中断信号，正在等待当前任务完成后退出...")
            interrupted = True

    original_handler = signal.signal(signal.SIGINT, handle_interrupt)

    for i, task in enumerate(tasks):
        if interrupted:
            results.append(TaskResult(task=task, row_index=i + 1, status="skipped", error_message="用户中断"))
            continue
        result = _execute_single_task(task, i + 1, client, config, lambda: interrupted)
        results.append(result)
        if progress_callback:
            progress_callback(i + 1, total, result)

    signal.signal(signal.SIGINT, original_handler)
    if concat:
        _concat_videos(results, config.output_dir, concat_name)
    return results


# ── 并行模式（新增） ──────────────────────────────
def _run_parallel(tasks, client, config, progress_callback, concat, concat_name):
    total = len(tasks)
    logger = logging.getLogger(__name__)

    # Phase 1: Generate reference images
    logger.info("阶段1/4: 生成参考图...")
    for i, task in enumerate(tasks):
        if task.image_prompts and not task.image:
            urls = [client.generate_image(p, size=_image_size(task, config)) for p in task.image_prompts]
            task.image = urls
        elif task.image_prompt and not task.image:
            task.image = [client.generate_image(task.image_prompt, size=_image_size(task, config))]

    # Phase 2: Submit all tasks
    logger.info("阶段2/4: 并行提交任务...")
    pending: list[dict] = []  # {task, row_idx, video_id, start, attempt}

    for i, task in enumerate(tasks):
        try:
            video_id = client.submit_task(task, defaults=config)
            pending.append({"task": task, "row_idx": i + 1, "video_id": video_id,
                            "start": time.monotonic(), "attempt": 1})
        except (ApiError, NetworkError) as e:
            _report_progress(progress_callback, i + 1, total,
                             TaskResult(task=task, row_index=i + 1, status="failed", error_message=str(e)))

    logger.info(f"  已提交 {len(pending)}/{total} 个任务")

    # Phase 3: Batch poll until all done
    logger.info("阶段3/4: 轮询生成结果...")
    completed_videos: list[dict] = []

    while pending:
        still_pending = []
        for p in pending:
            try:
                status = client.query_task(p["video_id"])
            except (ApiError, NetworkError):
                still_pending.append(p)
                continue

            if status.status == "completed" and status.video_url:
                p["video_url"] = status.video_url
                completed_videos.append(p)
            elif status.status == "failed":
                err = status.error or "生成失败"
                logger.warning(f"  第{p['row_idx']}行 失败: {err}")
                _report_progress(progress_callback, p["row_idx"], total,
                                 TaskResult(task=p["task"], row_index=p["row_idx"], status="failed",
                                            video_id=p["video_id"], error_message=err))
            else:
                still_pending.append(p)

        pending = still_pending
        if pending:
            time.sleep(config.poll_interval)

    # Phase 4: Download all
    logger.info(f"阶段4/4: 下载 {len(completed_videos)} 个视频...")
    results: list[TaskResult] = []
    for i, p in enumerate(completed_videos):
        try:
            out_path = Path(config.output_dir) / _build_output_filename(p["row_idx"], p["task"].prompt or "")
            client.download_video(p["video_url"], out_path)
            result = TaskResult(task=p["task"], row_index=p["row_idx"], status="success",
                                video_id=p["video_id"], output_path=str(out_path),
                                duration_seconds=time.monotonic() - p["start"])
            results.append(result)
            _report_progress(progress_callback, i + 1, total, result)
        except (ApiError, NetworkError) as e:
            results.append(TaskResult(task=p["task"], row_index=p["row_idx"], status="failed",
                                      video_id=p["video_id"], error_message=str(e)))

    results.sort(key=lambda r: r.row_index)

    if concat:
        _concat_videos(results, config.output_dir, concat_name)

    return results


def _report_progress(cb, current, total, result):
    if cb:
        cb(current, total, result)


# ── 单任务执行（串行使用） ───────────────────────
def _execute_single_task(
    task: TaskConfig,
    row_index: int,
    client: AgnesClient,
    config: AppConfig,
    interrupted: Callable[[], bool],
) -> TaskResult:
    start_time = time.monotonic()
    last_error: str | None = None

    for attempt in range(1, config.max_retries + 1):
        if interrupted():
            return TaskResult(task=task, row_index=row_index, status="interrupted",
                              error_message="用户中断", duration_seconds=time.monotonic() - start_time)
        try:
            if task.image_prompts and not task.image:
                task.image = [client.generate_image(p, size=_image_size(task, config)) for p in task.image_prompts]
            elif task.image_prompt and not task.image:
                task.image = [client.generate_image(task.image_prompt, size=_image_size(task, config))]

            video_id = client.submit_task(task, defaults=config)
            task_status = _poll_until_complete(client=client, video_id=video_id,
                                                poll_interval=config.poll_interval, interrupted=interrupted)

            if task_status.status == "completed" and task_status.video_url:
                output_path = Path(config.output_dir) / _build_output_filename(row_index, task.prompt or "")
                client.download_video(task_status.video_url, output_path)
                return TaskResult(task=task, row_index=row_index, status="success",
                                   video_id=video_id, output_path=str(output_path),
                                   duration_seconds=time.monotonic() - start_time)
            elif task_status.status == "interrupted":
                return TaskResult(task=task, row_index=row_index, status="interrupted",
                                   video_id=video_id, error_message="轮询过程中用户中断",
                                   duration_seconds=time.monotonic() - start_time)
            else:
                last_error = task_status.error or "生成失败"
        except (ApiError, NetworkError) as e:
            last_error = str(e)
            if attempt < config.max_retries:
                time.sleep(_backoff_delay(attempt))

    return TaskResult(task=task, row_index=row_index, status="failed",
                       error_message=last_error, duration_seconds=time.monotonic() - start_time)


def _poll_until_complete(client, video_id, poll_interval, interrupted):
    while True:
        if interrupted():
            return TaskStatus(video_id=video_id, status="interrupted", progress=0)
        status = client.query_task(video_id)
        if status.status in ("completed", "failed"):
            return status
        time.sleep(poll_interval)


def _backoff_delay(attempt: int) -> float:
    return 5.0 * attempt


def _build_output_filename(row_index: int, prompt: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    sanitized = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in prompt)
    sanitized = sanitized[:20].strip()
    return f"{row_index:04d}_{sanitized}_{ts}.mp4"


def _image_size(task: TaskConfig, config: AppConfig) -> str:
    w = task.width or config.default_width
    h = task.height or config.default_height
    return f"{w}x{h}"


def _concat_videos(results: list[TaskResult], output_dir: str, concat_name: str) -> Path | None:
    success_files = [Path(r.output_path) for r in results if r.status == "success" and r.output_path]
    if len(success_files) < 2:
        return None

    out_dir = Path(output_dir)
    concat_list = out_dir / "_concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for p in success_files:
            f.write(f"file '{p.resolve()}'\n")

    out_path = out_dir / concat_name
    try:
        subprocess.run(
            [FFMPEG_PATH, "-y", "-f", "concat", "-safe", "0",
             "-i", str(concat_list.resolve()), "-c", "copy", str(out_path.resolve())],
            capture_output=True, text=True, check=True, encoding="utf-8", errors="replace",
        )
        logger = logging.getLogger(__name__)
        logger.info(f"视频拼接完成: {out_path} ({out_path.stat().st_size / 1e6:.1f} MB)")
        return out_path
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logging.getLogger(__name__).warning(f"视频拼接失败: {e}")
        return None
    finally:
        if concat_list.exists():
            concat_list.unlink()