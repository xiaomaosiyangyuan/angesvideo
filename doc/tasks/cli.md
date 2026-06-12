# 模块 M1 — CLI 解析

**文件**：`cli.py`

**依赖**：`_constants.py`（默认值常量）

**被依赖**：`config.py`

---

## 子任务

- [x] 导入 `argparse` 和 `_constants` 中的默认值常量
- [x] 实现 `parse_args(argv: list[str] | None = None) -> argparse.Namespace` 函数
- [x] 注册 `--csv` 参数（`required=True`）
- [x] 注册 `--output` / `-o` 参数（默认 `DEFAULT_OUTPUT_DIR`）
- [x] 注册 `--key` / `-k` 参数（默认 `DEFAULT_KEY_FILE`）
- [x] 注册 `--interval` 参数（默认 `DEFAULT_POLL_INTERVAL`，int 类型）
- [x] 注册 `--max-retries` 参数（默认 `DEFAULT_MAX_RETRIES`，int 类型）
- [x] 注册 `--log` 参数（默认 `DEFAULT_LOG_FILE`）
- [x] 设置 `description="Agnes Video V2.0 批量视频生成工具"`

## 验收标准

- [x] `parse_args(["--csv", "tasks.csv"])` → `Namespace(csv="tasks.csv", output="./output", ...)` 其余字段为默认值
- [ ] `parse_args([])` → `SystemExit(2)`（缺少必填 --csv）
- [ ] `parse_args(["--csv", "t.csv", "--interval", "abc"])` → `SystemExit(2)`（类型错误）
- [ ] 代码通过 `mypy --strict` 和 `ruff check` 检测
