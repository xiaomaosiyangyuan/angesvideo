# 概要设计文档 — Agnes Video V2.0 批量视频生成工具

## 1. 模块划分

```
┌─────────────────────────────────────────────────────────────┐
│                        main.py                              │
│                    (主入口/编排器)                            │
└──────┬──────┬──────┬──────┬──────┬──────┬──────────────────┘
       │      │      │      │      │      │
       ▼      ▼      ▼      ▼      ▼      ▼
   ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐
   │CLI │ │Cfg │ │CSV │ │Val │ │API │ │Rpt │
   │    │ │    │ │Rdr │ │    │ │Cli │ │    │
   └────┘ └────┘ └────┘ └────┘ └────┘ └────┘
                                    │
                                    ▼
                               ┌────────┐
                               │ Runner │
                               │        │
                               └────────┘
```

| 编号 | 模块 | 文件名 | 职责 |
|------|------|--------|------|
| M1 | CLI 解析 | `cli.py` | 解析命令行参数 |
| M2 | 配置管理 | `config.py` | 管理 API Key、默认参数、运行时配置 |
| M3 | CSV 读取 | `reader.py` | 读取并解析 CSV 任务文件 |
| M4 | 参数校验 | `validator.py` | 校验单条任务的参数合法性 |
| M5 | API 客户端 | `api_client.py` | 封装 Agnes Video API 的 HTTP 通信 |
| M6 | 任务执行器 | `runner.py` | 串行执行批量任务（提交 → 轮询 → 下载） |
| M7 | 结果报告 | `reporter.py` | 输出 results.csv 和日志 |
| M0 | 主入口 | `main.py` / `batch_generate.py` | 编排所有模块，组织完整流程 |

---

## 2. 各模块详细设计

### 2.1 M0 — 主入口 (`main.py`)

**职责**：协调所有模块，组织完整运行流程。

**流程**：
```
CLI 解析参数
  → 加载配置
  → 读取 CSV 任务列表
  → 校验所有任务参数
  → 执行批量生成（Runner）
  → 输出结果报告
```

**依赖关系**：依赖 M1~M7 全部模块。

---

### 2.2 M1 — CLI 解析 (`cli.py`)

**职责**：解析命令行参数，返回结构化配置。

**接口**：

```python
def parse_args(argv: list[str] | None = None) -> argparse.Namespace
```

**返回值字段**：

| 字段 | 对应 CLI 参数 | 默认值 |
|------|--------------|--------|
| `csv_path` | `--csv` | 必填，无默认值 |
| `output_dir` | `--output` / `-o` | `./output` |
| `key_file` | `--key` / `-k` | `./key.txt` |
| `poll_interval` | `--interval` | `5`（秒） |
| `max_retries` | `--max-retries` | `3` |
| `log_file` | `--log` | `./batch.log` |

**依赖**：无。独立模块。

---

### 2.3 M2 — 配置管理 (`config.py`)

**职责**：合并 CLI 参数、文件配置（API Key）和默认参数，提供全局配置对象。

**数据类**：

```python
@dataclass
class AppConfig:
    api_key: str
    base_url: str = "https://apihub.agnes-ai.com/v1"
    csv_path: str
    output_dir: str
    poll_interval: int = 5
    max_retries: int = 3
    log_file: str = "./batch.log"

    # 以下为视频参数的全局默认值
    default_width: int = 1152
    default_height: int = 768
    default_num_frames: int = 121
    default_frame_rate: int = 24
```

**接口**：

```python
def load_config(args: argparse.Namespace) -> AppConfig
```

从 `key_file` 中读取 API Key（优先读主 Key 文件路径，若文件不存在则报错）。

**依赖**：依赖 M1（接收解析结果）。

---

### 2.4 M3 — CSV 读取 (`reader.py`)

**职责**：读取 CSV 文件，将每一行转换为 `TaskConfig` 对象。

**数据类**：

```python
@dataclass
class TaskConfig:
    prompt: str | None = None
    width: int | None = None       # None 表示使用全局默认值
    height: int | None = None
    num_frames: int | None = None
    frame_rate: int | None = None
    seed: int | None = None
    image: list[str] | None = None       # 从 "|" 分隔的字符串解析
    negative_prompt: str | None = None
    mode: str | None = None
    extra_body_image: list[str] | None = None
    extra_body_mode: str | None = None
```

**接口**：

```python
def read_tasks(csv_path: str) -> list[TaskConfig]
```

**规则**：
- 首行为表头，字段名与 `TaskConfig` 字段名一致（大小写敏感）
- 空字符串字段视为 `None`
- `image` 和 `extra_body_image` 列中如果包含 `|` 字符，按 `|` 拆分为列表
- `width`、`height`、`num_frames`、`frame_rate`、`seed` 自动转换为 int 类型
- 非法的类型转换抛出 `CsvParseError`（自定义异常，继承 ValueError）

**自定义异常**：

```python
class CsvParseError(ValueError):
    """CSV 解析错误，包含行号和错误信息"""
```

**依赖**：无。仅依赖 Python 标准库 `csv`。

---

### 2.5 M4 — 参数校验 (`validator.py`)

**职责**：校验单条 `TaskConfig` 的参数是否合法。

**接口**：

```python
def validate(task: TaskConfig) -> list[str]
```

返回错误信息列表，为空表示校验通过。

**校验规则**：

| 规则 | 说明 |
|------|------|
| `num_frames ≤ 441` | 超过最大帧数限制 |
| `num_frames 满足 8n+1` | 不满足公式时报错 |
| `num_frames ≥ 9` | 最少 9 帧 |
| `1 ≤ frame_rate ≤ 60` | 帧率超范围 |
| 至少提供 prompt 或 image 之一 | Text-to-Video 和 Image-to-Video 至少需要一个输入源 |
| `width` 和 `height` 均为正整数 | 分辨率合法 |

当 `num_frames` 为 `None`（使用默认值 121）时不触发帧数校验；当 `frame_rate` 为 `None`（使用默认值 24）时不触发帧率校验。

**自定义异常**：

```python
class ValidationError(ValueError):
    """参数校验失败"""
```

**依赖**：依赖 M3（`TaskConfig` 数据类）。

---

### 2.6 M5 — API 客户端 (`api_client.py`)

**职责**：封装与 Agnes Video V2.0 API 的所有 HTTP 通信。

**数据类**：

```python
@dataclass
class TaskStatus:
    video_id: str
    status: str           # "queued" | "processing" | "completed" | "failed"
    progress: int         # 0-100
    video_url: str | None # status 为 completed 时有值
    error: str | None     # status 为 failed 时有值
```

**接口**：

```python
class AgnesClient:
    def __init__(self, api_key: str, base_url: str = "https://apihub.agnes-ai.com/v1")

    def submit_task(self, task: TaskConfig) -> str
        # 返回 video_id
        # POST /v1/videos
        # 请求体: {
        #   "model": "agnes-video-v2.0",
        #   "prompt": ...,
        #   "height": ..., "width": ...,
        #   "num_frames": ..., "frame_rate": ...,
        #   "image": ...,
        #   "negative_prompt": ...,
        #   "seed": ...,
        #   "mode": ...,
        #   "extra_body": { "image": ..., "mode": ... }
        # }
        # 响应: { "video_id": "...", "status": "queued", ... }

    def query_task(self, video_id: str) -> TaskStatus
        # GET /agnesapi?video_id=<video_id>
        # 返回 TaskStatus

    def download_video(self, video_url: str, output_path: str) -> Path
        # 下载视频文件到本地
        # 返回下载后的文件路径
```

**错误处理**：
- HTTP 4xx/5xx 抛出 `ApiError`（自定义异常，含 status_code 和响应体）
- 网络异常抛出 `NetworkError`（自定义异常，含原始异常信息）
- 下载时检查 HTTP Content-Type，非 video/* 类型记录警告但继续保存

**自定义异常**：

```python
class ApiError(Exception):
    """API 返回错误"""
    def __init__(self, status_code: int, response_body: str, message: str = "")

class NetworkError(Exception):
    """网络请求失败"""
```

**依赖**：依赖 M3（`TaskConfig` 数据类）、第三方库 `requests`。

---

### 2.7 M6 — 任务执行器 (`runner.py`)

**职责**：串行执行批量任务，包含重试和轮询逻辑。

**数据类**：

```python
@dataclass
class TaskResult:
    task: TaskConfig
    row_index: int
    status: str              # "success" | "failed" | "skipped"
    video_id: str | None
    output_path: str | None
    error_message: str | None
    duration_seconds: float  # 该任务从提交到完成的总耗时
```

**接口**：

```python
def run_batch(
    tasks: list[TaskConfig],
    client: AgnesClient,
    config: AppConfig,
    progress_callback: Callable[[int, int, TaskResult], None] | None = None,
) -> list[TaskResult]
```

**执行逻辑**（伪代码）：

```
for i, task in enumerate(tasks):
    填充 task 中的 None 字段为全局默认值
    for attempt in 1..max_retries:
        ① client.submit_task(task) → video_id
        ② 循环:
            client.query_task(video_id) → status
            if status == "completed":
                client.download_video(...)
                记录 TaskResult(status="success")
                break
            elif status == "failed":
                记录错误，重试
            else:
                等待 poll_interval 秒，继续轮询
    if 所有重试均失败:
        记录 TaskResult(status="failed")
    调用 progress_callback(i+1, total, result)
```

**Ctrl+C 处理**：
- 捕获 `KeyboardInterrupt`
- 当前正在轮询/下载的任务标记为 `"interrupted"`
- 已完成的任务保持原有状态
- 未开始的任务不再执行
- 输出已完成的 results

**依赖**：依赖 M2（`AppConfig`）、M3（`TaskConfig`）、M5（`AgnesClient`、`TaskStatus`）。

---

### 2.8 M7 — 结果报告 (`reporter.py`)

**职责**：生成 results.csv 汇总报告，管理日志输出。

**接口**：

```python
def write_results_csv(results: list[TaskResult], output_dir: str) -> Path
    # 写入 output_dir/results.csv
    # 列: row_index, prompt, width, height, num_frames, frame_rate,
    #      seed, mode, status, video_id, output_path, error_message,
    #      duration_seconds
    # 返回生成的 CSV 文件路径

def setup_logger(log_file: str) -> logging.Logger
    # 配置日志：控制台输出（彩色）+ 文件输出
    # 返回配置好的 logger 实例
```

**日志格式**：
- 控制台：`[2026-06-11 20:50:00] INFO: 消息`（INFO 及以上级别，彩色输出）
- 文件：`[2026-06-11 20:50:00] INFO: 消息`（DEBUG 及以上级别，纯文本）

**依赖**：依赖 M6（`TaskResult`）。

---

## 3. 模块依赖关系图

```
                    ┌──────────┐
                    │  main.py │
                    └────┬─────┘
          ┌──────────────┼──────────────────┐
          │              │                  │
          ▼              ▼                  ▼
     ┌────────┐    ┌──────────┐     ┌──────────┐
     │ cli.py │    │ runner.py│     │reporter.py│
     └────┬───┘    └──┬────┬──┘     └──────────┘
          │           │    │
          ▼           │    │
     ┌────────┐       │    │
     │config.py│      │    │
     └────────┘       │    │
                      │    │
          ┌───────────┘    │
          ▼                ▼
     ┌──────────┐    ┌───────────┐
     │reader.py │    │api_client │
     └────┬─────┘    └─────┬─────┘
          │                │
          ▼                │
     ┌──────────┐          │
     │validator │          │
     └──────────┘          │
                           ▼
                    ┌──────────────┐
                    │  requests    │
                    │ (第三方库)    │
                    └──────────────┘
```

| 模块 | 直接依赖 | 间接依赖 |
|------|---------|---------|
| `cli.py` | 无 | 无 |
| `config.py` | `cli.py` | 无 |
| `reader.py` | 无 | 无 |
| `validator.py` | `reader.py`（`TaskConfig`） | 无 |
| `api_client.py` | `requests`、`reader.py`（`TaskConfig`） | 无 |
| `runner.py` | `config.py`、`reader.py`、`api_client.py` | `requests` |
| `reporter.py` | `runner.py`（`TaskResult`） | 无 |
| `main.py` | 全部模块 | `requests` |

---

## 4. 数据流

```
CLI args
   │
   ▼
AppConfig ─────────────────────────────────────┐
   │                                            │
   ▼                                            │
CSV 文件 ──▶ reader.py ──▶ list[TaskConfig]     │
                               │                │
                               ▼                │
                          validator.py          │
                          (校验通过后)            │
                               │                │
                               ▼                │
                    ┌────────────────────┐      │
                    │    runner.py       │      │
                    │  ┌──────────────┐  │      │
                    │  │ api_client   │  │      │
                    │  │ .submit()    │──┼──────┘ (使用 config)
                    │  │ .query()     │  │
                    │  │ .download()  │  │
                    │  └──────────────┘  │
                    └────────┬───────────┘
                             │
                             ▼
                    list[TaskResult]
                             │
                             ▼
                       reporter.py
                             │
                             ├──▶ results.csv
                             └──▶ batch.log (控制台 + 文件)
```

---

## 5. 文件结构

```
angesvideo/
├── batch_generate.py       # M0 主入口
├── cli.py                  # M1 CLI 解析
├── config.py               # M2 配置管理
├── reader.py               # M3 CSV 读取
├── validator.py            # M4 参数校验
├── api_client.py           # M5 API 客户端
├── runner.py               # M6 任务执行器
├── reporter.py             # M7 结果报告
├── doc/
│   ├── proposal.md         # 需求文档
│   └── high-level-design.md # 本文件
└── tests/
    ├── test_validator.py
    ├── test_reader.py
    ├── test_api_client.py
    └── test_runner.py
```

---

## 6. 测试要点

| 模块 | 核心测试场景 |
|------|-------------|
| `reader.py` | 标准 CSV 解析、空字段处理、`\|` 分隔解析、类型转换、文件不存在、非法 CSV 格式 |
| `validator.py` | 8n+1 规则校验、帧率范围、必填项检查、边界值（9/441 帧、1/60 FPS） |
| `api_client.py` | 正常提交流程、查询状态流转、下载成功/失败、HTTP 错误处理、超时 |
| `runner.py` | 正常批量完成、重试逻辑（成功/失败）、部分失败、Ctrl+C 中断 |
