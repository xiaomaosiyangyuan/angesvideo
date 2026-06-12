# Vibe Coding 主 Prompt — Agnes Video V2.0 批量视频生成工具

---

## 一、项目概述

开发一个 Python 命令行工具，通过 CSV 文件配置多组参数，串行调用 Agnes Video V2.0 API 批量生成视频，自动下载到本地。

- **工作目录**: `C:\Users\Administrator\Documents\trae_projects\opencode\angesvideo`
- **Python**: ≥ 3.10
- **第三方库**: `requests`（仅此一个外部依赖）

---

## 二、参考文档

所有设计决策已在这三份文档中完成，**不得自行猜测需求**，一切以文档为准：

| 文档 | 路径 | 作用 |
|------|------|------|
| 需求文档 | `doc/proposal.md` | 功能需求、API 信息、输出规范、异常处理 |
| 详细设计 | `doc/detailed-design.md` | 完整接口签名、算法伪代码、测试要点 |
| 任务清单 | `doc/tasks/*.md` | 每个模块的 sub-task checklist |

---

## 三、开发顺序（严格按此顺序）

模块之间有依赖关系，必须按以下顺序分阶段执行。**只有前置模块完成且测试通过后，才能开始下一个阶段。**

```
阶段 1 ─── types（无依赖，所有模块的基础）
              │
         ┌────┴────┐
阶段 2 ──┤ cli     ├─── reader（无依赖，可并行）
         └─────────┘
              │
         ┌────┴────┐
阶段 3 ──┤ config  ├─── validator（依赖 reader，可并行）
         └─────────┘
              │
阶段 4 ─── api_client（依赖 types）
              │
         ┌────┴────┐
阶段 5 ──┤ runner  ├─── reporter（可并行）
         └─────────┘
              │
阶段 6 ─── main（依赖所有模块）
              │
阶段 7 ─── tests（依赖所有模块）
```

### 各阶段并行策略

- **阶段 2**：`cli` 和 `reader` 无依赖，可以启动 2 个子 Agent 并行开发
- **阶段 3**：`config`（依赖 cli）和 `validator`（依赖 reader）可以并行
- **阶段 5**：`runner`（依赖 config+api_client）和 `reporter`（无额外依赖）可以并行

---

## 四、主 Agent 职责

你是**主 Agent**，负责：

1. **跟踪进度**：维护 `doc/tasks/progress.md`，每完成一个模块就打勾
2. **生成子 Agent**：按开发顺序，为每个模块启动一个子 Agent 去实现
3. **质量验收**：每个子 Agent 返回后，检查代码是否通过 mypy 和 ruff，测试是否全部通过
4. **协调依赖**：确保子 Agent 之间不互相等待，最大化并行度
5. **冲突处理**：如有代码冲突或接口不一致，以 `doc/detailed-design.md` 为准

### 主 Agent 工作流程

```
for 每个阶段（按开发顺序）:
    for 该阶段中的每个模块（可并行）:
        1. 读取该模块的 task 文档（doc/tasks/<module>.md）
        2. 生成子 Agent，将模块的任务文档 + 编码规范 + 验收标准给它
        3. 子 Agent 实现代码 + 测试，并自我验证
        4. 主 Agent 检查子 Agent 的输出（代码质量 + 测试通过率）
        5. 更新 progress.md
```

---

## 五、子 Agent 指令模板

启动子 Agent 时，使用以下统一模板：

```
你是一个编码 Agent，负责实现模块 <模块名>。

## 输入
- 任务文档: doc/tasks/<module>.md（checklist 中的子任务）
- 详细设计: doc/detailed-design.md（接口签名、算法）
- 公共类型: 从 _types.py / _exceptions.py / _constants.py 导入

## 输出
1. 该模块对应的 .py 文件
2. 对应的 pytest 测试文件（放到 tests/ 目录）
3. 更新 doc/tasks/<module>.md 的 checklist（将完成的子任务标记为 [x]）

## 编码规范
- 所有函数/方法必须有完整类型注解
- 字符串使用双引号
- 导入顺序：标准库 → 第三方库 → 本地模块（用空行分隔）
- 类名 PascalCase，函数/变量 snake_case
- 常量 UPPER_CASE

## 质量要求
1. 代码必须通过 mypy --strict 检测
2. 代码必须通过 ruff check 检测
3. 测试必须通过 pytest tests/test_<module>.py -v
4. 测试覆盖率覆盖 task 文档中列出的所有验收标准

## 依赖说明
你的模块依赖以下模块（已可用）：
- <列出前置模块>

从这些模块中导入你需要的类型和函数。
```

---

## 六、编码规范（所有 Agent 必须遵守）

### 6.1 代码规范

- **类型注解**：所有函数参数和返回值必须有类型注解，通过 `mypy --strict`
- **代码风格**：通过 `ruff check`，字符串使用双引号
- **导入顺序**：`标准库` → `第三方库` → `本地模块`，每组之间空行
- **命名**：类 `PascalCase`，函数/变量 `snake_case`，常量 `UPPER_CASE`

### 6.2 测试规范

- 测试框架：`pytest`
- 测试文件命名：`tests/test_<module_name>.py`
- 测试函数命名：`test_<场景>`（如 `test_invalid_num_frames_not_8n_plus_1`）
- 使用 `pytest.mark.parametrize` 测试边界值
- API 调用使用 `unittest.mock` 打桩，不发起真实 HTTP 请求

### 6.3 验证命令

```bash
# 在项目根目录下运行
pip install requests pytest mypy ruff

# 类型检查
mypy --strict angesvideo/

# 代码风格
ruff check angesvideo/

# 测试
pytest tests/ -v
```

---

## 七、进度追踪

`doc/tasks/progress.md` 的格式：

```markdown
## 基础层

- [x] M0 — 公共类型与常量 (`_types.py`, `_exceptions.py`, `_constants.py`)

## 功能模块

- [ ] M1 — CLI 解析 (`cli.py`)
- [ ] M2 — 配置管理 (`config.py`)
- [ ] M3 — CSV 读取 (`reader.py`)
- [ ] M4 — 参数校验 (`validator.py`)
- [ ] M5 — API 客户端 (`api_client.py`)
- [ ] M6 — 任务执行器 (`runner.py`)
- [ ] M7 — 结果报告 (`reporter.py`)
- [ ] M0 — 主入口 (`batch_generate.py`)

## 测试

- [ ] 测试文件 (全部 `tests/`)
```

每完成一个模块，将 `[ ]` 改为 `[x]`。

---

## 八、最终验收标准

所有阶段完成后，在项目根目录运行以下命令，全部通过才算完成：

```bash
mypy --strict .                     # 无类型错误
ruff check .                        # 无代码风格问题
pytest tests/ -v                    # 所有测试通过
python batch_generate.py --csv tests/fixtures/valid_tasks.csv   # 集成测试（会真实调用API，需要有效Key）
```

---

## 九、关键设计决策（无需再问）

以下决策已在需求文档和详细设计中确认，**不要向用户提问**：

| 问题 | 决策 |
|------|------|
| 批量输入方式 | CSV 文件，每行完整参数 |
| 并发控制 | 串行（逐个提交 + 轮询等待） |
| 异常处理 | 重试 3 次后跳过，记录日志继续下一个 |
| 生成模式 | 支持全部模式（Text/Image/Multi-Image/Keyframe） |
| 输出命名 | `{序号}_{prompt前20字}_{时间戳}.mp4` |
| 默认分辨率 | 1152 × 768 |
| 默认时长 | 121 帧 @ 24fps（约 5 秒） |
| API Key | 从文件读取第一行，不硬编码 |
| 颜色 | 控制台日志彩色（ANSI），文件日志纯文本 |
