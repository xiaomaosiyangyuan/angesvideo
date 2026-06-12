# 模块 M3 — CSV 读取

**文件**：`reader.py`

**依赖**：`_types.py`（`TaskConfig`）、`_exceptions.py`（`CsvParseError`）

**被依赖**：`batch_generate.py`

---

## 子任务

- [x] 定义 `FIELD_MAP`（CSV 列名 → TaskConfig 字段名映射，11 个字段）
- [x] 定义 `INT_FIELDS` 集合（`width`, `height`, `num_frames`, `frame_rate`, `seed`）
- [x] 定义 `LIST_FIELDS` 集合（`image`, `extra_body_image`）
- [x] 实现 `read_tasks(csv_path: str) -> list[TaskConfig]` 主函数
- [x] 文件不存在时抛出 `FileNotFoundError`
- [x] 使用 `csv.DictReader` 解析 CSV
- [x] 无表头或空文件时抛出 `CsvParseError`
- [x] 无数据行时抛出 `CsvParseError`
- [x] 实现 `_parse_row(row: dict[str, str]) -> TaskConfig` 辅助函数
- [x] 空字符串字段解析为 `None`
- [x] `INT_FIELDS` 自动 `int()` 转换，失败时抛出 `CsvParseError`（含行号）
- [x] `LIST_FIELDS` 按 `|` 分隔并 strip，空列表转为 `None`
- [x] 字符串字段直接 `strip()`
- [x] 未知列忽略

## 验收标准

- [x] 标准 3 行 CSV → 返回 `list[TaskConfig]` 长度 3，类型正确
- [x] 空字段 → 对应 `TaskConfig` 字段为 `None`
- [ ] `image` 列 `"a.jpg|b.jpg"` → `TaskConfig.image == ["a.jpg", "b.jpg"]`
- [ ] `width` 列 `"abc"` → 抛出 `CsvParseError(row_index=2)`
- [ ] 不存在的 CSV 路径 → `FileNotFoundError`
- [ ] 代码通过 `mypy --strict` 和 `ruff check` 检测
