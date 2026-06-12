# 详细设计文档 — Agnes Video V2.0 批量视频生成工具

## 0. 公共约定

### 0.1 类型别名与公共数据类

所有公共数据类和类型别名定义在 `_types.py` 中，各模块从中导入。

```python
# _types.py

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TaskConfig:
    """单条视频生成任务的参数配置。None 表示使用全局默认值。"""
    prompt: str | None = None
    width: int | None = None
    height: int | None = None
    num_frames: int | None = None
    frame_rate: int | None = None
    seed: int | None = None
    image: list[str] | None = None
    negative_prompt: str | None = None
    mode: str | None = None          # "ti2vid" | "keyframes"
    extra_body_image: list[str] | None = None
    extra_body_mode: str | None = None


@dataclass
class AppConfig:
    """全局运行时配置，合并 CLI 参数、Key 文件、默认值后的最终配置。"""
    api_key: str
    base_url: str = "https://apihub.agnes-ai.com/v1"
    csv_path: str = ""
    output_dir: str = "./output"
    poll_interval: int = 5
    max_retries: int = 3
    log_file: str = "./batch.log"

    # 视频参数全局默认值
    default_width: int = 1152
    default_height: int = 768
    default_num_frames: int = 121
    default_frame_rate: int = 24


@dataclass
class TaskStatus:
    """API 查询返回的任务状态。"""
    video_id: str
    status: str               # "queued" | "processing" | "completed" | "failed"
    progress: int = 0         # 0-100
    video_url: str | None = None
    error: str | None = None


@dataclass
class TaskResult:
    """单条任务执行完毕后的结果记录。"""
    task: TaskConfig
    row_index: int
    status: str               # "success" | "failed" | "skipped" | "interrupted"
    video_id: str | None = None
    output_path: str | None = None
    error_message: str | None = None
    duration_seconds: float = 0.0
```

### 0.2 自定义异常

```python
# _exceptions.py

class CsvParseError(ValueError):
    """CSV 解析错误。"""
    def __init__(self, message: str, row_index: int | None = None):
        self.row_index = row_index
        super().__init__(message)


class ValidationError(ValueError):
    """参数校验失败。"""
    pass


class ApiError(Exception):
    """API 返回错误响应。"""
    def __init__(self, status_code: int, response_body: str, message: str = ""):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message or f"API 错误 {status_code}: {response_body[:200]}")


class NetworkError(Exception):
    """网络请求失败（超时、断连等）。"""
    pass
```

### 0.3 通用常量

```python
# _constants.py

VALID_NUM_FRAMES = {8 * n + 1 for n in range(1, 56)}  # 9, 17, 25, ..., 441
MIN_FRAME_RATE = 1
MAX_FRAME_RATE = 60
DEFAULT_POLL_INTERVAL = 5
DEFAULT_MAX_RETRIES = 3
DEFAULT_OUTPUT_DIR = "./output"
DEFAULT_LOG_FILE = "./batch.log"
DEFAULT_KEY_FILE = "./key.txt"
MAX_FRAMES = 441
MIN_FRAMES = 9
DOWNLOAD_RETRIES = 2
DOWNLOAD_RETRY_DELAY = 5
```

---

## 1. M1 — CLI 解析 (`cli.py`)

### 1.1 接口定义

```python
import argparse

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
```

### 1.2 参数说明

| 参数 | 标志 | type | default | help |
|------|------|------|---------|------|
| CSV 路径 | `--csv` | `str` | 必填 | 任务 CSV 文件路径 |
| 输出目录 | `--output`, `-o` | `str` | `"./output"` | 视频下载目录 |
| Key 文件 | `--key`, `-k` | `str` | `"./key.txt"` | API Key 文件路径 |
| 轮询间隔 | `--interval` | `int` | `5` | 轮询间隔（秒） |
| 最大重试 | `--max-retries` | `int` | `3` | 单任务最大重试次数 |
| 日志文件 | `--log` | `str` | `"./batch.log"` | 日志文件路径 |

### 1.3 算法

```python
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
    return parser.parse_args(argv)
```

### 1.4 测试要点

| 测试场景 | 输入 | 预期 |
|---------|------|------|
| 完整参数 | `["--csv", "tasks.csv", "-o", "./vid", "-k", "./key.txt"]` | `Namespace(csv_path="tasks.csv", output_dir="./vid", ...)` |
| 仅必填 | `["--csv", "tasks.csv"]` | 其余字段使用默认值 |
| 缺少 --csv | `[]` | `SystemExit(2)` |
| 非法 --interval | `["--csv", "t.csv", "--interval", "abc"]` | `SystemExit(2)` |

---

## 2. M2 — 配置管理 (`config.py`)

### 2.1 接口定义

```python
def load_config(args: argparse.Namespace) -> AppConfig
```

### 2.2 算法

```python
def load_config(args: argparse.Namespace) -> AppConfig:
    # 1. 读取 API Key 文件
    key_path = Path(args.key)
    if not key_path.exists():
        raise FileNotFoundError(f"API Key 文件不存在: {key_path}")
    api_key = key_path.read_text(encoding="utf-8").strip()

    # 2. 构建 AppConfig
    return AppConfig(
        api_key=api_key,
        csv_path=args.csv,
        output_dir=args.output,
        poll_interval=args.interval,
        max_retries=args.max_retries,
        log_file=args.log,
    )
```

### 2.3 Key 文件格式

- 第一行为 API Key，忽略空白行和后续行
- 示例内容（`key.txt`）：
  ```
  sk-fWJBRvCxQ5Z3yAFjDENbgTp15uJO86CMVaWyeDemxbx23IBV
  ```

### 2.4 测试要点

| 测试场景 | 输入 | 预期 |
|---------|------|------|
| Key 文件正常 | 文件内容含 Key | `AppConfig.api_key == "sk-..."` |
| Key 文件不存在 | 路径无效 | 抛出 `FileNotFoundError` |
| Key 文件含空白行 | 第一行 Key，空行，多余行 | 正确提取第一行 |

---

## 3. M3 — CSV 读取 (`reader.py`)

### 3.1 接口定义

```python
def read_tasks(csv_path: str) -> list[TaskConfig]
```

### 3.2 算法

```python
import csv
from pathlib import Path

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
        # 校验表头
        if not reader.fieldnames:
            raise CsvParseError("CSV 文件为空或缺少表头")

        for row_idx, row in enumerate(reader, start=2):  # 行号从 2 开始（1 是表头）
            try:
                task = _parse_row(row)
                tasks.append(task)
            except (ValueError, TypeError) as e:
                raise CsvParseError(f"第 {row_idx} 行解析失败: {e}", row_index=row_idx) from e

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
            kwargs[task_field] = parts if parts else None
        else:
            kwargs[task_field] = raw.strip()

    return TaskConfig(**kwargs)
```

### 3.3 CSV 列名与 TaskConfig 字段映射

CSV 表头必须与 `FIELD_MAP` 中的 key 完全匹配（大小写敏感）。不在映射表中的列将被忽略。

### 3.4 测试要点

| 测试场景 | 输入 | 预期 |
|---------|------|------|
| 标准 CSV | 3 行完整参数 | 返回 3 个 TaskConfig，类型正确 |
| 空字段 | 某列为空字符串 | 对应字段为 None |
| 多图 URL | `image` 列为 `a.jpg\|b.jpg\|c.jpg` | `image == ["a.jpg","b.jpg","c.jpg"]` |
| 类型转换 | `width` 为 `"abc"` | 抛出 `CsvParseError` |
| 文件不存在 | 路径无效 | 抛出 `FileNotFoundError` |
| 空文件 | 仅表头无数据 | 抛出 `CsvParseError` |
| 无表头 | 纯数据无表头 | `fieldnames` 为 None 时抛出 `CsvParseError` |

---

## 4. M4 — 参数校验 (`validator.py`)

### 4.1 接口定义

```python
def validate(task: TaskConfig) -> list[str]
```

### 4.2 算法

```python
VALID_NUM_FRAMES = {8 * n + 1 for n in range(1, 56)}

def validate(task: TaskConfig) -> list[str]:
    errors: list[str] = []

    # 1. 至少提供 prompt 或 image 之一
    if not task.prompt and not task.image:
        errors.append("至少需要提供 prompt 或 image 之一")

    # 2. num_frames 校验（仅在非 None 时触发）
    if task.num_frames is not None:
        if task.num_frames < MIN_FRAMES:
            errors.append(f"num_frames({task.num_frames}) 不能小于 {MIN_FRAMES}")
        elif task.num_frames > MAX_FRAMES:
            errors.append(f"num_frames({task.num_frames}) 不能超过 {MAX_FRAMES}")
        elif task.num_frames not in VALID_NUM_FRAMES:
            errors.append(
                f"num_frames({task.num_frames}) 不满足 8n+1 公式，合法值: 9, 17, 25, ..., 441"
            )

    # 3. frame_rate 校验
    if task.frame_rate is not None:
        if task.frame_rate < MIN_FRAME_RATE or task.frame_rate > MAX_FRAME_RATE:
            errors.append(f"frame_rate({task.frame_rate}) 超出范围 [{MIN_FRAME_RATE}, {MAX_FRAME_RATE}]")

    # 4. width / height 校验
    if task.width is not None and task.width <= 0:
        errors.append(f"width({task.width}) 必须为正整数")
    if task.height is not None and task.height <= 0:
        errors.append(f"height({task.height}) 必须为正整数")

    # 5. mode 校验
    if task.mode is not None and task.mode not in ("ti2vid", "keyframes"):
        errors.append(f"mode({task.mode}) 必须为 'ti2vid' 或 'keyframes'")

    return errors
```

### 4.3 测试要点

| 测试场景 | 输入 | 预期 |
|---------|------|------|
| 合法任务 | prompt="cat", num_frames=121 | 返回 `[]` |
| 帧数不满足 8n+1 | num_frames=100 | 返回含错误信息的列表 |
| 帧数超上限 | num_frames=500 | 返回含错误信息的列表 |
| 帧数低于下限 | num_frames=5 | 返回含错误信息的列表 |
| 帧率超范围 | frame_rate=100 | 返回含错误信息的列表 |
| 无 prompt 无 image | prompt=None, image=None | 返回含错误信息的列表 |
| None 字段不触发校验 | num_frames=None, frame_rate=None | 不报帧数/帧率错误 |
| 非法 mode | mode="invalid" | 返回含错误信息的列表 |
| width 为 0 | width=0 | 返回含错误信息的列表 |

---

## 5. M5 — API 客户端 (`api_client.py`)

### 5.1 接口定义

```python
class AgnesClient:
    def __init__(self, api_key: str, base_url: str = "https://apihub.agnes-ai.com/v1")

    def submit_task(self, task: TaskConfig, defaults: AppConfig | None = None) -> str

    def query_task(self, video_id: str) -> TaskStatus

    def download_video(self, video_url: str, output_path: str | Path) -> Path
```

### 5.2 实现细节

#### 5.2.1 `submit_task`

```python
def submit_task(self, task: TaskConfig, defaults: AppConfig | None = None) -> str:
    """提交视频生成任务，返回 video_id。"""
    # 1. 构建请求体
    body = {
        "model": "agnes-video-v2.0",
    }

    # 填充非 None 字段
    candidates = {
        "prompt": task.prompt,
        "height": task.height,
        "width": task.width,
        "num_frames": task.num_frames,
        "frame_rate": task.frame_rate,
        "negative_prompt": task.negative_prompt,
        "seed": task.seed,
        "mode": task.mode,
    }
    for key, val in candidates.items():
        if val is not None:
            body[key] = val

    # 填充默认值（当 defaults 提供且对应字段为 None 时）
    if defaults:
        if task.height is None:
            body["height"] = defaults.default_height
        if task.width is None:
            body["width"] = defaults.default_width
        if task.num_frames is None:
            body["num_frames"] = defaults.default_num_frames
        if task.frame_rate is None:
            body["frame_rate"] = defaults.default_frame_rate

    # extra_body
    extra: dict[str, object] = {}
    if task.extra_body_image is not None:
        extra["image"] = task.extra_body_image
    if task.extra_body_mode is not None:
        extra["mode"] = task.extra_body_mode
    if extra:
        body["extra_body"] = extra

    # image 字段：单图传 string，多图传 list
    if task.image is not None:
        if len(task.image) == 1:
            body["image"] = task.image[0]
        else:
            body["image"] = task.image

    # 2. 发送 POST 请求
    try:
        resp = requests.post(
            f"{self.base_url}/v1/videos",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=(10, 60),  # connect=10s, read=60s
        )
    except requests.exceptions.Timeout as e:
        raise NetworkError(f"提交任务超时: {e}") from e
    except requests.exceptions.ConnectionError as e:
        raise NetworkError(f"网络连接失败: {e}") from e

    if not resp.ok:
        raise ApiError(resp.status_code, resp.text)

    data = resp.json()
    video_id = data.get("video_id") or data.get("id") or data.get("task_id")
    if not video_id:
        raise ApiError(resp.status_code, resp.text, "响应中未找到 video_id")
    return str(video_id)
```

#### 5.2.2 `query_task`

```python
def query_task(self, video_id: str) -> TaskStatus:
    """查询任务状态。"""
    try:
        resp = requests.get(
            f"{self.base_url}/agnesapi",
            params={"video_id": video_id},
            headers={
                "Authorization": f"Bearer {self.api_key}",
            },
            timeout=(10, 30),
        )
    except requests.exceptions.Timeout as e:
        raise NetworkError(f"查询任务状态超时: {e}") from e
    except requests.exceptions.ConnectionError as e:
        raise NetworkError(f"网络连接失败: {e}") from e

    if not resp.ok:
        raise ApiError(resp.status_code, resp.text)

    data = resp.json()
    return TaskStatus(
        video_id=str(data.get("video_id", video_id)),
        status=str(data.get("status", "unknown")),
        progress=int(data.get("progress", 0)),
        video_url=data.get("video_url") or data.get("url") or data.get("result"),
        error=data.get("error"),
    )
```

#### 5.2.3 `download_video`

```python
def download_video(self, video_url: str, output_path: str | Path) -> Path:
    """下载视频文件到本地。"""
    output_path = Path(output_path)

    for attempt in range(1, DOWNLOAD_RETRIES + 1):
        try:
            resp = requests.get(
                video_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=(10, 120),
                stream=True,
            )
        except requests.exceptions.RequestException as e:
            if attempt < DOWNLOAD_RETRIES:
                time.sleep(DOWNLOAD_RETRY_DELAY)
                continue
            raise NetworkError(f"下载失败（已重试 {DOWNLOAD_RETRIES} 次）: {e}") from e

        if not resp.ok:
            raise ApiError(resp.status_code, resp.text, f"下载视频失败")

        # 检查 Content-Type
        content_type = resp.headers.get("Content-Type", "")
        if not content_type.startswith("video/") and content_type:
            # 非 video 类型，记录警告但继续保存
            import logging
            logging.getLogger(__name__).warning(
                f"Content-Type 不是 video/*: {content_type}，继续保存"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        return output_path

    # 所有重试失败
    raise NetworkError(f"下载失败（已重试 {DOWNLOAD_RETRIES} 次）")
```

### 5.3 测试要点

| 测试场景 | 方法 | 预期 |
|---------|------|------|
| 提交成功 | `submit_task` | 返回 video_id 字符串 |
| 提交时 HTTP 4xx | `submit_task` | 抛出 `ApiError` |
| 提交超时 | `submit_task` | 抛出 `NetworkError` |
| 查询状态 completed | `query_task` | `TaskStatus(status="completed", video_url="...")` |
| 查询状态 failed | `query_task` | `TaskStatus(status="failed", error="...")` |
| 查询网络异常 | `query_task` | 抛出 `NetworkError` |
| 下载成功 | `download_video` | 返回实际下载路径，文件存在且大小 > 0 |
| 下载 HTTP 错误 | `download_video` | 抛出 `ApiError` |
| 下载重试后仍失败 | `download_video` | 抛出 `NetworkError` |

---

## 6. M6 — 任务执行器 (`runner.py`)

### 6.1 接口定义

```python
from collections.abc import Callable

ProgressCallback = Callable[[int, int, TaskResult], None]

def run_batch(
    tasks: list[TaskConfig],
    client: AgnesClient,
    config: AppConfig,
    progress_callback: ProgressCallback | None = None,
) -> list[TaskResult]
```

### 6.2 算法

```python
import time
import signal
from datetime import datetime, timezone

def run_batch(
    tasks: list[TaskConfig],
    client: AgnesClient,
    config: AppConfig,
    progress_callback: ProgressCallback | None = None,
) -> list[TaskResult]:
    """串行执行批量任务。"""
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
    return results


def _execute_single_task(
    task: TaskConfig,
    row_index: int,
    client: AgnesClient,
    config: AppConfig,
    interrupted: Callable[[], bool],
) -> TaskResult:
    """执行单条任务，含重试逻辑。"""
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
            # 步骤 1：提交任务
            video_id = client.submit_task(task, defaults=config)

            # 步骤 2：轮询状态
            task_status = _poll_until_complete(
                client=client, video_id=video_id,
                poll_interval=config.poll_interval,
                interrupted=interrupted,
            )

            if task_status.status == "completed" and task_status.video_url:
                # 步骤 3：下载视频
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
                # status == "failed"
                last_error = task_status.error or "生成失败"

        except (ApiError, NetworkError) as e:
            last_error = str(e)
            if attempt < config.max_retries:
                wait = _backoff_delay(attempt)
                time.sleep(wait)

    # 所有重试均失败
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
    """轮询直到任务完成或失败。"""
    while True:
        if interrupted():
            return TaskStatus(video_id=video_id, status="interrupted", progress=0)

        status = client.query_task(video_id)

        if status.status in ("completed", "failed"):
            return status

        time.sleep(poll_interval)


def _backoff_delay(attempt: int) -> float:
    """退避延迟：第 1 次重试等 5s，第 2 次等 10s。"""
    return 5.0 * attempt


def _build_output_filename(row_index: int, prompt: str) -> str:
    """构建输出文件名。"""
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    sanitized = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in prompt)
    sanitized = sanitized[:20].strip()
    return f"{row_index:04d}_{sanitized}_{ts}.mp4"
```

### 6.3 测试要点

| 测试场景 | 预期 |
|---------|------|
| 3 个任务全部成功 | 返回 3 个 `TaskResult(status="success")` |
| 第 2 个任务失败，重试 3 次后跳过 | 返回 3 个结果，第 2 个 `status="failed"` |
| 第 1 次提交失败，第 2 次重试成功 | 最终 `status="success"` |
| 轮询中收到 failed 状态 | `TaskResult(status="failed")` |
| Ctrl+C 中断处理 | 已完成任务为 success，未开始为 skipped，当前为 interrupted |
| progress_callback 被正确调用 | 回调收到 (i+1, total, result) |
| 文件名生成 | `0001_A cat walking on bea_20260611_205000.mp4`（prompt 截取 20 字符，特殊字符替换为 `_`） |

---

## 7. M7 — 结果报告 (`reporter.py`)

### 7.1 接口定义

```python
def write_results_csv(results: list[TaskResult], output_dir: str) -> Path

def setup_logger(log_file: str) -> logging.Logger
```

### 7.2 实现

#### 7.2.1 `write_results_csv`

```python
def write_results_csv(results: list[TaskResult], output_dir: str) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "results.csv"

    fieldnames = [
        "row_index", "status", "prompt", "width", "height",
        "num_frames", "frame_rate", "seed", "mode",
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
                "video_id": r.video_id or "",
                "output_path": r.output_path or "",
                "error_message": r.error_message or "",
                "duration_seconds": f"{r.duration_seconds:.1f}",
            })

    return csv_path
```

#### 7.2.2 `setup_logger`

```python
import logging

def setup_logger(log_file: str) -> logging.Logger:
    logger = logging.getLogger("agnes_video_batch")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    formatter_file = logging.Formatter(
        "[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 文件 Handler：DEBUG 级别
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter_file)
    logger.addHandler(file_handler)

    # 控制台 Handler：INFO 级别，彩色输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(_ColoredFormatter(
        "[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(console_handler)

    return logger


class _ColoredFormatter(logging.Formatter):
    """控制台彩色日志格式器。"""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[41m",  # Red bg
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        levelname = record.levelname
        color = self.COLORS.get(levelname, "")
        record.levelname = f"{color}{levelname}{self.RESET}"
        return super().format(record)
```

### 7.3 测试要点

| 测试场景 | 预期 |
|---------|------|
| 写入 results.csv | 文件存在，表头正确，数量与结果一致 |
| 空结果列表 | CSV 仅包含表头行 |
| 彩色控制台日志 | 日志内容正确，包含级别颜色代码 |
| 文件日志含 DEBUG | 文件日志包含 DEBUG 级别信息 |

---

## 8. M0 — 主入口 (`batch_generate.py`)

### 8.1 接口定义

```python
def main() -> None
```

### 8.2 算法

```python
import sys

def main() -> None:
    # 1. 解析 CLI 参数
    args = cli.parse_args()

    # 2. 加载配置
    try:
        config = config_module.load_config(args)
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    # 3. 设置日志
    logger = reporter.setup_logger(config.log_file)
    logger.info("=" * 50)
    logger.info("Agnes Video V2.0 批量视频生成工具")
    logger.info(f"CSV: {config.csv_path}")
    logger.info(f"输出: {config.output_dir}")
    logger.info("=" * 50)

    # 4. 读取 CSV
    try:
        tasks = reader.read_tasks(config.csv_path)
        logger.info(f"读取到 {len(tasks)} 条任务")
    except (FileNotFoundError, CsvParseError) as e:
        logger.error(f"读取 CSV 失败: {e}")
        sys.exit(1)

    # 5. 校验参数
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

    # 6. 创建 API 客户端
    client = AgnesClient(api_key=config.api_key, base_url=config.base_url)

    # 7. 执行批量生成
    logger.info("开始批量生成...")

    def progress_callback(current: int, total: int, result: TaskResult) -> None:
        status_icon = {
            "success": "✓",
            "failed": "✗",
            "skipped": "→",
            "interrupted": "⚠",
        }.get(result.status, "?")
        logger.info(
            f"[{current}/{total}] {status_icon} 第 {result.row_index} 行 "
            f"- {result.status}"
            + (f" - {result.output_path}" if result.output_path else "")
            + (f" - {result.error_message}" if result.error_message else "")
        )

    results = runner.run_batch(tasks, client, config, progress_callback=progress_callback)

    # 8. 输出报告
    csv_path = reporter.write_results_csv(results, config.output_dir)
    logger.info(f"结果报告已保存: {csv_path}")

    # 9. 统计
    success_count = sum(1 for r in results if r.status == "success")
    failed_count = sum(1 for r in results if r.status == "failed")
    skipped_count = sum(1 for r in results if r.status in ("skipped", "interrupted"))
    logger.info("=" * 50)
    logger.info(f"全部完成: 成功 {success_count} / 失败 {failed_count} / 跳过 {skipped_count}")
    logger.info("=" * 50)

    if failed_count > 0:
        sys.exit(1)
```

### 8.3 依赖关系（完整导入）

```python
# batch_generate.py

import sys
from pathlib import Path

from _types import TaskConfig, AppConfig, TaskResult
from _exceptions import CsvParseError
import cli
import config as config_module
import reader
import validator
from api_client import AgnesClient
import runner
import reporter
```

---

## 9. 测试文件规划

### 9.1 测试目录结构

```
tests/
├── __init__.py
├── test_cli.py
├── test_config.py
├── test_reader.py
├── test_validator.py
├── test_api_client.py
├── test_runner.py
├── test_reporter.py
├── fixtures/
│   ├── valid_tasks.csv
│   ├── empty.csv
│   └── key.txt
```

### 9.2 各文件测试重点

| 测试文件 | 测试内容 |
|---------|---------|
| `test_cli.py` | 各参数组合解析、缺失必填参数、非法类型 |
| `test_config.py` | Key 文件读取、文件不存在、含空白行 |
| `test_reader.py` | CSV 解析（单元测试，不依赖文件系统时用 `csv.StringIO`） |
| `test_validator.py` | 所有校验规则的分支覆盖 |
| `test_api_client.py` | 使用 `responses` 或 `unittest.mock` mock HTTP 请求 |
| `test_runner.py` | mock `AgnesClient`，测试重试、中断、轮询逻辑 |
| `test_reporter.py` | CSV 写入、日志格式器 |

### 9.3 关键测试用例（`test_validator.py` 示例）

```python
# tests/test_validator.py

import pytest
from _types import TaskConfig
from validator import validate


def test_valid_task():
    task = TaskConfig(prompt="cat", num_frames=121, frame_rate=24)
    assert validate(task) == []


def test_invalid_num_frames_not_8n_plus_1():
    task = TaskConfig(prompt="cat", num_frames=100)
    errors = validate(task)
    assert len(errors) == 1
    assert "8n+1" in errors[0]


def test_num_frames_none_skips_validation():
    task = TaskConfig(prompt="cat", num_frames=None)
    assert validate(task) == []


@pytest.mark.parametrize("frames", [9, 17, 25, 33, 41, 49, 57, 65, 73, 81, 121, 241, 441])
def test_valid_num_frames_boundaries(frames: int):
    task = TaskConfig(prompt="cat", num_frames=frames)
    assert validate(task) == []


@pytest.mark.parametrize("frames", [8, 10, 16, 18, 440, 442])
def test_invalid_num_frames_boundaries(frames: int):
    task = TaskConfig(prompt="cat", num_frames=frames)
    errors = validate(task)
    assert len(errors) >= 1
```

---

## 10. 模块文件总览

| 文件 | 对应模块 | 主要导出 |
|------|---------|---------|
| `_types.py` | 公共类型 | `TaskConfig`, `AppConfig`, `TaskStatus`, `TaskResult` |
| `_exceptions.py` | 公共异常 | `CsvParseError`, `ValidationError`, `ApiError`, `NetworkError` |
| `_constants.py` | 公共常量 | `VALID_NUM_FRAMES`, `MIN_FRAME_RATE`, `MAX_FRAME_RATE` 等 |
| `cli.py` | M1 | `parse_args()` |
| `config.py` | M2 | `load_config()` |
| `reader.py` | M3 | `read_tasks()` |
| `validator.py` | M4 | `validate()` |
| `api_client.py` | M5 | `AgnesClient` 类 |
| `runner.py` | M6 | `run_batch()` |
| `reporter.py` | M7 | `write_results_csv()`, `setup_logger()` |
| `batch_generate.py` | M0 | `main()` |