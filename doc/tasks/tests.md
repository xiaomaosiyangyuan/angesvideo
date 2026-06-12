# 测试文件

**目录**：`tests/`

**依赖**：全部模块 + 第三方库 `pytest`

---

## 子任务

### 基础设施

- [ ] 创建 `tests/__init__.py`（空文件）
- [ ] 创建 `tests/fixtures/` 目录
- [ ] 创建 `tests/fixtures/valid_tasks.csv`（3 行有效数据，包含各种类型字段）
- [ ] 创建 `tests/fixtures/empty.csv`（仅表头，无数据）
- [ ] 创建 `tests/fixtures/key.txt`（含有效格式的 API Key）

### test_cli.py

- [ ] 完整参数解析
- [ ] 仅必填参数（检查默认值）
- [ ] 缺少 `--csv` 时 `SystemExit`
- [ ] `--interval` 传入非法字符串时 `SystemExit`

### test_config.py

- [ ] 正常 Key 文件读取
- [ ] Key 文件不存在时 `FileNotFoundError`
- [ ] Key 文件含多余空白行

### test_reader.py

- [ ] 标准 CSV 解析（长度、字段类型）
- [ ] 空字段解析为 None
- [ ] 多图 URL 的 `|` 分隔
- [ ] 类型转换失败时 `CsvParseError`
- [ ] 文件不存在时 `FileNotFoundError`
- [ ] 无数据行时 `CsvParseError`

### test_validator.py

- [ ] 合法任务返回 `[]`
- [ ] 非法帧数（不满足 8n+1）
- [ ] 帧数超出上限
- [ ] 帧数低于下限
- [ ] 帧率超范围
- [ ] 无 prompt 无 image
- [ ] None 字段不触发校验
- [ ] 非法 mode
- [ ] width/height ≤ 0
- [ ] 边界值 parametrize（9 个合法值 + 6 个非法值）

### test_api_client.py

- [ ] `submit_task` 成功（mock `requests.post` 返回 video_id）
- [ ] `submit_task` HTTP 4xx → `ApiError`
- [ ] `submit_task` 超时 → `NetworkError`
- [ ] `query_task` 返回 `completed` → `TaskStatus(video_url=...)`
- [ ] `query_task` 返回 `failed` → `TaskStatus(error=...)`
- [ ] `query_task` 网络异常 → `NetworkError`
- [ ] `download_video` 成功 → 文件路径正确、文件存在
- [ ] `download_video` HTTP 错误 → `ApiError`
- [ ] `download_video` 重试后失败 → `NetworkError`

### test_runner.py

- [ ] 全部成功（mock `AgnesClient`）
- [ ] 部分失败（重试后仍失败）
- [ ] 重试成功（首次失败，第二次成功）
- [ ] Ctrl+C 中断（mock `signal.signal` 或使用线程模拟）
- [ ] progress_callback 调用次数

### test_reporter.py

- [ ] `write_results_csv` 写入内容和表头正确
- [ ] 空结果列表
- [ ] `setup_logger` 返回有效 logger
- [ ] `_ColoredFormatter` 颜色代码

## 验收标准

- [ ] 所有测试通过：`pytest tests/ -v`
- [ ] 代码通过 `mypy --strict` 和 `ruff check` 检测
