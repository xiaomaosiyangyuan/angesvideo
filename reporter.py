import csv
import logging
from pathlib import Path

from _types import TaskResult


def write_results_csv(results: list[TaskResult], output_dir: str) -> Path:
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    csv_path = out_path / "results.csv"

    fieldnames = [
        "row_index", "status", "prompt", "width", "height",
        "num_frames", "frame_rate", "seed", "mode",
        "image_prompt", "image_prompts", "image", "extra_body_image",
        "video_id", "output_path", "error_message", "duration_seconds",
    ]

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "row_index": r.row_index,
                "status": r.status,
                "prompt": r.task.prompt or "",
                "width": r.task.width or "",
                "height": r.task.height or "",
                "num_frames": r.task.num_frames or "",
                "frame_rate": r.task.frame_rate or "",
                "seed": r.task.seed or "",
                "mode": r.task.mode or "",
                "image_prompt": r.task.image_prompt or "",
                "image_prompts": "|".join(r.task.image_prompts) if r.task.image_prompts else "",
                "image": "|".join(r.task.image) if r.task.image else "",
                "extra_body_image": "|".join(r.task.extra_body_image) if r.task.extra_body_image else "",
                "video_id": r.video_id or "",
                "output_path": r.output_path or "",
                "error_message": r.error_message or "",
                "duration_seconds": f"{r.duration_seconds:.1f}",
            })

    return csv_path


def setup_logger(log_file: str) -> logging.Logger:
    logger = logging.getLogger("agnes_video_batch")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    formatter_file = logging.Formatter(
        "[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter_file)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(_ColoredFormatter(
        "[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(console_handler)

    return logger


class _ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[41m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        levelname = record.levelname
        color = self.COLORS.get(levelname, "")
        record.levelname = f"{color}{levelname}{self.RESET}"
        return super().format(record)