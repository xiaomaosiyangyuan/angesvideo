from dataclasses import dataclass


@dataclass
class TaskConfig:
    prompt: str | None = None
    width: int | None = None
    height: int | None = None
    num_frames: int | None = None
    frame_rate: int | None = None
    seed: int | None = None
    image: list[str] | None = None
    image_prompt: str | None = None
    negative_prompt: str | None = None
    mode: str | None = None
    extra_body_image: list[str] | None = None
    extra_body_mode: str | None = None


@dataclass
class AppConfig:
    api_key: str
    base_url: str = "https://apihub.agnes-ai.com"
    csv_path: str = ""
    output_dir: str = "./output"
    poll_interval: int = 5
    max_retries: int = 3
    log_file: str = "./batch.log"
    default_width: int = 1152
    default_height: int = 768
    default_num_frames: int = 121
    default_frame_rate: int = 24


@dataclass
class TaskStatus:
    video_id: str
    status: str
    progress: int = 0
    video_url: str | None = None
    error: str | None = None


@dataclass
class TaskResult:
    task: TaskConfig
    row_index: int
    status: str
    video_id: str | None = None
    output_path: str | None = None
    error_message: str | None = None
    duration_seconds: float = 0.0