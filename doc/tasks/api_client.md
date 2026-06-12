# 模块 M5 — API 客户端

**文件**：`api_client.py`

**依赖**：`_types.py`（`TaskConfig`, `AppConfig`, `TaskStatus`）、`_exceptions.py`（`ApiError`, `NetworkError`）、`_constants.py`（`DOWNLOAD_RETRIES`, `DOWNLOAD_RETRY_DELAY`）、第三方库 `requests`

**被依赖**：`runner.py`

---

## 子任务

### 类初始化

- [ ] 定义 `AgnesClient` 类，`__init__(self, api_key: str, base_url: str = "https://apihub.agnes-ai.com/v1")`
- [ ] 保存 `api_key` 和 `base_url` 到实例属性

### submit_task

- [ ] 实现 `submit_task(self, task: TaskConfig, defaults: AppConfig | None = None) -> str`
- [ ] 构建请求体：固定 `model: "agnes-video-v2.0"`
- [ ] 填充非 None 的顶层字段（prompt/height/width/num_frames/frame_rate/negative_prompt/seed/mode）
- [ ] 当 `defaults` 提供时，回填 None 字段为全局默认值
- [ ] 处理 `image`：单元素传 string，多元素传 list
- [ ] 处理 `extra_body`：仅在有值时添加
- [ ] POST `{base_url}/v1/videos`，`timeout=(10, 60)`
- [ ] 异常处理：`Timeout` → `NetworkError`，`ConnectionError` → `NetworkError`
- [ ] 非 2xx 响应 → `ApiError`
- [ ] 从响应中提取 `video_id`（按 `video_id` → `id` → `task_id` 降序尝试）
- [ ] 找不到 `video_id` 时抛出 `ApiError`

### query_task

- [ ] 实现 `query_task(self, video_id: str) -> TaskStatus`
- [ ] GET `{base_url}/agnesapi?video_id={video_id}`，`timeout=(10, 30)`
- [ ] 异常处理同上
- [ ] 解析响应 JSON 到 `TaskStatus`（`video_url` 按 `video_url` → `url` → `result` 降序尝试）

### download_video

- [ ] 实现 `download_video(self, video_url: str, output_path: str | Path) -> Path`
- [ ] 使用 `stream=True` 流式下载
- [ ] 检查 Content-Type，非 video/* 时记录 warning 但继续
- [ ] 自动创建父目录
- [ ] 写入 8192 bytes 块
- [ ] 重试逻辑：最多 `DOWNLOAD_RETRIES(2)` 次，间隔 `DOWNLOAD_RETRY_DELAY(5)` 秒
- [ ] 所有重试失败后抛出 `NetworkError`

## 验收标准

- [ ] `submit_task` 成功返回 video_id 字符串
- [ ] `submit_task` HTTP 4xx → `ApiError(status_code=...)`
- [ ] `submit_task` 网络超时 → `NetworkError`
- [ ] `query_task` 返回 `completed` → `TaskStatus(status="completed", video_url="...")`
- [ ] `query_task` HTTP 错误 → `ApiError`
- [ ] `download_video` 成功 → 文件存在且大小 > 0
- [ ] `download_video` HTTP 错误 → `ApiError`
- [ ] 代码通过 `mypy --strict` 和 `ruff check` 检测
