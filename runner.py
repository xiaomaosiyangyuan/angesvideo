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
) -> list[TaskResult]:
    results: list[TaskResult] = []
    interrupted = False
    total = len(tasks)

    def handle_interrupt(signum: object, frame: object) -> None:
        nonlocal interrupted
        if not interrupted:
            print("\n收到中断信号，正在等待当前任务完成后退出...")
            interrupted = True

    original_handler = signal.signal(signal.SIGINT, handle_interrupt)

    for i, task in enumerate(tasks):
        if interrupted:
            results.append(TaskResult(
                task=task, row_index=i + 1, status="skipped",
                error_message="用户中断",
            ))
            continue

        result = _execute_single_task(
            task=task, row_index=i + 1,
            client=client, config=config,
            interrupted=lambda: interrupted,
        )
        results.append(result)

        if progress_callback:
            progress_callback(i + 1, total, result)

    signal.signal(signal.SIGINT, original_handler)

    if concat:
        _concat_videos(results, config.output_dir, concat_name)

    return results


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
            return TaskResult(
                task=task, row_index=row_index, status="interrupted",
                error_message="用户中断",
                duration_seconds=time.monotonic() - start_time,
            )

        try:
            if task.image_prompts and not task.image:
                urls = []
                for i, p in enumerate(task.image_prompts):
                    url = client.generate_image(p, size=_image_size(task, config))
                    urls.append(url)
                task.image = urls
            elif task.image_prompt and not task.image:
                image_url = client.generate_image(
                    task.image_prompt,
                    size=_image_size(task, config),
                )
                task.image = [image_url]

            video_id = client.submit_task(task, defaults=config)

            task_status = _poll_until_complete(
                client=client, video_id=video_id,
                poll_interval=config.poll_interval,
                interrupted=interrupted,
            )

            if task_status.status == "completed" and task_status.video_url:
                output_filename = _build_output_filename(
                    row_index=row_index, prompt=task.prompt or "",
                )
                output_path = Path(config.output_dir) / output_filename
                client.download_video(task_status.video_url, output_path)

                return TaskResult(
                    task=task, row_index=row_index, status="success",
                    video_id=video_id, output_path=str(output_path),
                    duration_seconds=time.monotonic() - start_time,
                )
            elif task_status.status == "interrupted":
                return TaskResult(
                    task=task, row_index=row_index, status="interrupted",
                    video_id=video_id, error_message="轮询过程中用户中断",
                    duration_seconds=time.monotonic() - start_time,
                )
            else:
                last_error = task_status.error or "生成失败"

        except (ApiError, NetworkError) as e:
            last_error = str(e)
            if attempt < config.max_retries:
                wait = _backoff_delay(attempt)
                time.sleep(wait)

    return TaskResult(
        task=task, row_index=row_index, status="failed",
        error_message=last_error,
        duration_seconds=time.monotonic() - start_time,
    )


def _poll_until_complete(
    client: AgnesClient,
    video_id: str,
    poll_interval: int,
    interrupted: Callable[[], bool],
) -> TaskStatus:
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
    success_files = [
        Path(r.output_path) for r in results
        if r.status == "success" and r.output_path
    ]
    if len(success_files) < 2:
        return None

    out_dir = Path(output_dir)
    concat_list = out_dir / "_concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for p in success_files:
            f.write(f"file '{p.resolve()}'\n")

    out_path = out_dir / concat_name
    try:
        result = subprocess.run(
            [FFMPEG_PATH, "-y", "-f", "concat", "-safe", "0",
             "-i", str(concat_list.resolve()), "-c", "copy", str(out_path.resolve())],
            capture_output=True, text=True, check=True,
            encoding="utf-8", errors="replace",
        )
        size = out_path.stat().st_size
        logger = logging.getLogger(__name__)
        logger.info(f"视频拼接完成: {out_path} ({size / 1e6:.1f} MB)")
        return out_path
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"视频拼接失败: {e}")
        return None
    finally:
        if concat_list.exists():
            concat_list.unlink()

