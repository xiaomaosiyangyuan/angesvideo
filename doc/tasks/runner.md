# 模块 M6 — 任务执行器

**文件**：`runner.py`

**依赖**：`_types.py`（`TaskConfig`, `AppConfig`, `TaskStatus`, `TaskResult`）、`api_client.py`（`AgnesClient`）、`_constants.py`

**被依赖**：`batch_generate.py`

---

## 子任务

- [ ] 定义 `ProgressCallback = Callable[[int, int, TaskResult], None]` 类型别名

### run_batch（主函数）

- [ ] 实现 `run_batch(tasks, client, config, progress_callback=None) -> list[TaskResult]`
- [ ] 使用 `signal.signal(signal.SIGINT, handler)` 捕获 Ctrl+C
- [ ] 中断处理器设置 `interrupted = True`，打印提示信息
- [ ] 串行遍历 tasks：
  - 已中断 → 标记为 `"skipped"` 并 continue
  - 调用 `_execute_single_task`
  - 调用 `progress_callback(i+1, total, result)`
- [ ] 执行完毕后恢复原始信号处理器

### _execute_single_task

- [ ] 实现 `_execute_single_task(task, row_index, client, config, interrupted) -> TaskResult`
- [ ] 记录 `start_time = time.monotonic()`
- [ ] 重试循环（`1..config.max_retries`）：
  - 检查 `interrupted()` → 返回 `"interrupted"`
  - 调用 `client.submit_task(task, defaults=config)`
  - 调用 `_poll_until_complete`
  - 成功（`completed` + video_url）→ 下载视频，返回 `"success"`
  - 中断（`interrupted`）→ 返回 `"interrupted"`
  - 失败（`failed`）→ 记录错误，继续重试循环
- [ ] 捕获 `ApiError` / `NetworkError` → 退避等待后重试
- [ ] 所有重试失败 → 返回 `"failed"`

### _poll_until_complete

- [ ] 实现 `_poll_until_complete(client, video_id, poll_interval, interrupted) -> TaskStatus`
- [ ] 循环：检查中断 → `query_task` → `completed/failed` 时返回 → 否则 sleep `poll_interval`

### _backoff_delay

- [ ] 实现 `_backoff_delay(attempt: int) -> float`：`5.0 * attempt`

### _build_output_filename

- [ ] 实现 `_build_output_filename(row_index: int, prompt: str) -> str`
- [ ] 格式：`{row_index:04d}_{prompt sanitized}_{timestamp}.mp4`
- [ ] sanitize：非字母数字和空格/`-`/`_` 的字符替换为 `_`，截取 20 字符后 strip

## 验收标准

- [ ] 3 个任务全部 mock 成功 → 3 个 `TaskResult(status="success")`
- [ ] 第 2 个任务 mock 失败（重试 3 次）→ 第 2 个 `status="failed"`
- [ ] 第 1 次提交失败，第 2 次重试成功 → 最终 `status="success"`
- [ ] 轮询返回 `failed` 状态 → `TaskResult(status="failed")`
- [ ] Ctrl+C 中断 → 已完成为 success，当前为 interrupted，未开始为 skipped
- [ ] progress_callback 接收正确参数
- [ ] `_build_output_filename(1, "A cat @ beach!")` → `"0001_A cat _ beach__20260611_205000.mp4"`
- [ ] 代码通过 `mypy --strict` 和 `ruff check` 检测
