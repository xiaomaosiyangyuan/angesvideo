# 模块 M0 — 公共类型与常量

**文件**：`_types.py`, `_exceptions.py`, `_constants.py`

**依赖**：无（纯数据定义，被所有模块依赖）

---

## 子任务

### _types.py

- [x] 定义 `TaskConfig` 数据类（11 个字段，`prompt` / `width` / `height` / `num_frames` / `frame_rate` / `seed` / `image` / `negative_prompt` / `mode` / `extra_body_image` / `extra_body_mode`）
- [x] 定义 `AppConfig` 数据类（`api_key` / `base_url` / `csv_path` / `output_dir` / `poll_interval` / `max_retries` / `log_file` + 4 个默认值字段）
- [x] 定义 `TaskStatus` 数据类（`video_id` / `status` / `progress` / `video_url` / `error`）
- [x] 定义 `TaskResult` 数据类（`task` / `row_index` / `status` / `video_id` / `output_path` / `error_message` / `duration_seconds`）

### _exceptions.py

- [x] 定义 `CsvParseError(ValueError)` — 含 `row_index` 属性
- [x] 定义 `ValidationError(ValueError)`
- [x] 定义 `ApiError(Exception)` — 含 `status_code` / `response_body` 属性
- [x] 定义 `NetworkError(Exception)`

### _constants.py

- [x] 定义 `VALID_NUM_FRAMES`（8n+1 集合，9~441）
- [x] 定义 `MIN_FRAME_RATE` / `MAX_FRAME_RATE`
- [x] 定义 `DEFAULT_POLL_INTERVAL` / `DEFAULT_MAX_RETRIES` / `DEFAULT_OUTPUT_DIR` / `DEFAULT_LOG_FILE` / `DEFAULT_KEY_FILE`
- [x] 定义 `MAX_FRAMES` / `MIN_FRAMES`
- [x] 定义 `DOWNLOAD_RETRIES` / `DOWNLOAD_RETRY_DELAY`

## 验收标准

- [x] 所有数据类可通过 `from _types import TaskConfig` 正常导入
- [x] 所有异常类可通过 `from _exceptions import ApiError` 正常导入
- [x] 所有常量可通过 `from _constants import VALID_NUM_FRAMES` 正常导入
- [x] `TaskConfig` 实例可以正常创建，None 字段不报错
- [x] `CsvParseError("msg", row_index=5).row_index == 5`
- [x] `ApiError(400, "bad request").status_code == 400`
- [ ] 代码通过 `mypy --strict` 和 `ruff check` 检测
