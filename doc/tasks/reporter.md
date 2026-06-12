# 模块 M7 — 结果报告

**文件**：`reporter.py`

**依赖**：`_types.py`（`TaskResult`）、`_constants.py`

**被依赖**：`batch_generate.py`

---

## 子任务

### write_results_csv

- [ ] 实现 `write_results_csv(results: list[TaskResult], output_dir: str) -> Path`
- [ ] 自动创建 `output_dir` 目录
- [ ] 写入 `results.csv`，编码 `utf-8`，`newline=""`
- [ ] 表头：`row_index`, `status`, `prompt`, `width`, `height`, `num_frames`, `frame_rate`, `seed`, `mode`, `video_id`, `output_path`, `error_message`, `duration_seconds`
- [ ] 每行数据从 `TaskResult` 和 `TaskConfig` 提取
- [ ] None 字段写入空字符串
- [ ] `duration_seconds` 格式化为 `"{:.1f}"`

### setup_logger

- [ ] 实现 `setup_logger(log_file: str) -> logging.Logger`
- [ ] Logger 名称 `"agnes_video_batch"`，级别 `DEBUG`
- [ ] 清空已有 handlers
- [ ] 文件 Handler：`DEBUG` 级别，格式 `[%(asctime)s] %(levelname)s: %(message)s`
- [ ] 控制台 Handler：`INFO` 级别，使用 `_ColoredFormatter`

### _ColoredFormatter

- [ ] 实现 `_ColoredFormatter(logging.Formatter)`
- [ ] 定义颜色映射：DEBUG=Cyan, INFO=Green, WARNING=Yellow, ERROR=Red, CRITICAL=Red bg
- [ ] `format()` 方法给 `levelname` 包上 ANSI 颜色代码

## 验收标准

- [ ] `write_results_csv([result1, result2], "/tmp/out")` → `/tmp/out/results.csv` 存在，2 行数据 + 表头
- [ ] `write_results_csv([], "/tmp/out")` → CSV 仅表头行
- [ ] `setup_logger("/tmp/test.log")` 返回 logger
- [ ] 控制台日志包含 ANSI 颜色代码
- [ ] 文件日志包含 DEBUG 级别
- [ ] 代码通过 `mypy --strict` 和 `ruff check` 检测
