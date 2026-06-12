from _constants import MAX_FRAMES, MAX_FRAME_RATE, MIN_FRAMES, MIN_FRAME_RATE, VALID_NUM_FRAMES
from _types import TaskConfig


def validate(task: TaskConfig) -> list[str]:
    errors: list[str] = []

    if not task.prompt and not task.image:
        errors.append("至少需要提供 prompt 或 image 之一")

    if task.num_frames is not None:
        if task.num_frames < MIN_FRAMES:
            errors.append(f"num_frames({task.num_frames}) 不能小于 {MIN_FRAMES}")
        elif task.num_frames > MAX_FRAMES:
            errors.append(f"num_frames({task.num_frames}) 不能超过 {MAX_FRAMES}")
        elif task.num_frames not in VALID_NUM_FRAMES:
            errors.append(
                f"num_frames({task.num_frames}) 不满足 8n+1 公式，合法值: 9, 17, 25, ..., 441",
            )

    if task.frame_rate is not None:
        if task.frame_rate < MIN_FRAME_RATE or task.frame_rate > MAX_FRAME_RATE:
            errors.append(
                f"frame_rate({task.frame_rate}) 超出范围 [{MIN_FRAME_RATE}, {MAX_FRAME_RATE}]",
            )

    if task.width is not None and task.width <= 0:
        errors.append(f"width({task.width}) 必须为正整数")

    if task.height is not None and task.height <= 0:
        errors.append(f"height({task.height}) 必须为正整数")

    if task.mode is not None and task.mode not in ("ti2vid", "keyframes"):
        errors.append(f"mode({task.mode}) 必须为 'ti2vid' 或 'keyframes'")

    return errors