# 模块 M2 — 配置管理

**文件**：`config.py`

**依赖**：`_types.py`（`AppConfig`）、`cli.py`（`parse_args`）

**被依赖**：`batch_generate.py`

---

## 子任务

- [x] 实现 `load_config(args: argparse.Namespace) -> AppConfig` 函数
- [x] 从 `args.key` 路径读取 API Key 文件（`Path.read_text(encoding="utf-8").strip()`）
- [x] Key 文件不存在时抛出 `FileNotFoundError`
- [x] 正确映射 CLI 参数到 `AppConfig` 字段
- [x] 设置 `base_url` 固定为 `"https://apihub.agnes-ai.com/v1"`

## 验收标准

- [x] Key 文件存在时：返回 `AppConfig(api_key="sk-...", csv_path=..., ...)`
- [x] Key 文件不存在时：抛出 `FileNotFoundError`
- [x] Key 文件第一行为 Key，后续空行不干扰
- [ ] 代码通过 `mypy --strict` 和 `ruff check` 检测
