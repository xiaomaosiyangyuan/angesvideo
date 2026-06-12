# 模块 M4 — 参数校验

**文件**：`validator.py`

**依赖**：`_types.py`（`TaskConfig`）、`_constants.py`（`VALID_NUM_FRAMES` / `MIN_FRAMES` / `MAX_FRAMES` / `MIN_FRAME_RATE` / `MAX_FRAME_RATE`）

**被依赖**：`batch_generate.py`

---

## 子任务

- [x] 实现 `validate(task: TaskConfig) -> list[str]` 函数
- [x] 校验规则 1：`prompt` 和 `image` 至少提供一个
- [x] 校验规则 2：`num_frames` 非 None 时 — 不能小于 `MIN_FRAMES(9)`
- [x] 校验规则 3：`num_frames` 非 None 时 — 不能大于 `MAX_FRAMES(441)`
- [x] 校验规则 4：`num_frames` 非 None 时 — 必须在 `VALID_NUM_FRAMES` 集合中（8n+1）
- [x] 校验规则 5：`frame_rate` 非 None 时 — 必须在 `[MIN_FRAME_RATE, MAX_FRAME_RATE]` 范围内
- [x] 校验规则 6：`width` 非 None 且 `≤ 0` 时报错
- [x] 校验规则 7：`height` 非 None 且 `≤ 0` 时报错
- [x] 校验规则 8：`mode` 非 None 且不是 `"ti2vid"` 或 `"keyframes"` 时报错
- [x] 所有 None 字段不触发对应校验

## 验收标准

- [x] `validate(TaskConfig(prompt="cat", num_frames=121, frame_rate=24))` → `[]`
- [x] `validate(TaskConfig(prompt="cat", num_frames=100))` → 1 个错误含 "8n+1"
- [x] `validate(TaskConfig(prompt="cat", num_frames=500))` → 1 个错误含 "441"
- [x] `validate(TaskConfig(prompt="cat", num_frames=5))` → 1 个错误含 "9"
- [x] `validate(TaskConfig(prompt="cat", frame_rate=100))` → 1 个错误
- [x] `validate(TaskConfig(prompt="cat", width=0))` → 1 个错误
- [x] `validate(TaskConfig(prompt=None, image=None))` → 1 个错误
- [x] `validate(TaskConfig(prompt="cat", num_frames=None))` → `[]`（不触发帧数校验）
- [x] `validate(TaskConfig(prompt="cat", mode="invalid"))` → 1 个错误
- [x] `pytest.mark.parametrize` 测试 9 个合法帧数 + 6 个非法帧数边界值
- [ ] 代码通过 `mypy --strict` 和 `ruff check` 检测
