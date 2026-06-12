# 模块 M0 — 主入口

**文件**：`batch_generate.py`

**依赖**：全部模块（`_types`, `_exceptions`, `cli`, `config`, `reader`, `validator`, `api_client`, `runner`, `reporter`）

**被依赖**：无（入口文件）

---

## 子任务

- [ ] 导入所有依赖模块
- [ ] 实现 `main() -> None` 函数

### main 流程

- [ ] 步骤 1：调用 `cli.parse_args()` 解析参数
- [ ] 步骤 2：调用 `config.load_config(args)` 加载配置（捕获 `FileNotFoundError` 并 `sys.exit(1)`）
- [ ] 步骤 3：调用 `reporter.setup_logger(log_file)` 设置日志
- [ ] 步骤 4：打印启动信息（工具名称、CSV 路径、输出目录）
- [ ] 步骤 5：调用 `reader.read_tasks(csv_path)` 读取任务（捕获异常并 `sys.exit(1)`）
- [ ] 步骤 6：遍历所有任务，调用 `validator.validate(task)` 校验
- [ ] 步骤 7：校验失败时打印错误并 `sys.exit(1)`
- [ ] 步骤 8：创建 `AgnesClient` 实例
- [ ] 步骤 9：定义 `progress_callback`（带状态图标：✓/✗/→/⚠）
- [ ] 步骤 10：调用 `runner.run_batch(...)` 执行
- [ ] 步骤 11：调用 `reporter.write_results_csv(...)` 输出报告
- [ ] 步骤 12：统计并打印完成信息（成功/失败/跳过）
- [ ] 步骤 13：有失败任务时 `sys.exit(1)`
- [ ] 确保 `if __name__ == "__main__": main()` 入口

## 验收标准

- [ ] `main()` 完整流程跑通（集成测试）
- [ ] CSV 文件不存在时 → 打印错误并 exit(1)
- [ ] Key 文件不存在时 → 打印错误并 exit(1)
- [ ] 参数校验失败 → 打印具体错误并 exit(1)
- [ ] 成功生成视频后 → output 目录有视频文件 + results.csv
- [ ] 代码通过 `mypy --strict` 和 `ruff check` 检测
