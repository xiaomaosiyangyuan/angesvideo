import csv
from pathlib import Path

from _exceptions import CsvParseError
from _types import TaskConfig

FIELD_MAP = {
    "prompt": "prompt",
    "width": "width",
    "height": "height",
    "num_frames": "num_frames",
    "frame_rate": "frame_rate",
    "seed": "seed",
    "image": "image",
    "negative_prompt": "negative_prompt",
    "mode": "mode",
    "extra_body_image": "extra_body_image",
    "extra_body_mode": "extra_body_mode",
}

INT_FIELDS = {"width", "height", "num_frames", "frame_rate", "seed"}
LIST_FIELDS = {"image", "extra_body_image"}


def read_tasks(csv_path: str) -> list[TaskConfig]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV 文件不存在: {csv_path}")

    tasks: list[TaskConfig] = []
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise CsvParseError("CSV 文件为空或缺少表头")

        for row_idx, row in enumerate(reader, start=2):
            try:
                task = _parse_row(row)
                tasks.append(task)
            except (ValueError, TypeError) as e:
                raise CsvParseError(
                    f"第 {row_idx} 行解析失败: {e}", row_index=row_idx,
                ) from e

    if not tasks:
        raise CsvParseError("CSV 文件中没有数据行")

    return tasks


def _parse_row(row: dict[str, str]) -> TaskConfig:
    kwargs: dict[str, object] = {}

    for csv_field, task_field in FIELD_MAP.items():
        raw = row.get(csv_field, "")
        if raw is None or raw.strip() == "":
            continue

        if csv_field in INT_FIELDS:
            kwargs[task_field] = int(raw)
        elif csv_field in LIST_FIELDS:
            parts = [p.strip() for p in raw.split("|") if p.strip()]
            if parts:
                kwargs[task_field] = parts
        else:
            kwargs[task_field] = raw.strip()

    return TaskConfig(**kwargs)  # type: ignore[arg-type]