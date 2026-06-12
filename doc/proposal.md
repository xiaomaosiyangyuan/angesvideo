# 项目需求文档 — Agnes Video V2.0 批量视频生成工具

## 1. 项目概述

开发一个 Python 命令行工具，通过 CSV 文件配置多组参数，**串行**调用 Agnes Video V2.0 API 批量生成视频，自动下载到本地。

## 2. API 信息

| 项目 | 值 |
|------|-----|
| 模型 | `agnes-video-v2.0` |
| 请求端点 | `POST https://apihub.agnes-ai.com/v1/videos` |
| 查询端点 | `GET https://apihub.agnes-ai.com/agnesapi?video_id=<VIDEO_ID>` |
| 调用方式 | 异步（提交任务 → 轮询结果 → 下载视频） |
| 认证方式 | HTTP Header `Authorization: Bearer <API_KEY>` |

### 2.1 API Key 来源

- **主 Key**（`anges.txt`）：`sk-fWJBRvCxQ5Z3yAFjDENbgTp15uJO86CMVaWyeDemxbx23IBV`
- **备选 Key**（`SenseNova.txt`）：`sk-2jkk2EIAXRsKqPgWqPeeKYCKJpVFIn44`
- Base URL：`https://apihub.agnes-ai.com/v1`

工具应支持从配置文件读取 Key，不应硬编码在代码中。

### 2.2 视频参数约束

| 参数 | 约束 |
|------|------|
| 最大帧数 | ≤ 441 |
| 帧数规则 | 必须满足 `8n + 1`（如 9, 17, 25, ..., 441） |
| 帧率范围 | 1 ~ 60 FPS |
| 默认分辨率 | 1152 × 768 |
| 默认配置 | num_frames=121, frame_rate=24（约 5 秒） |

### 2.3 预设时长（24 FPS）

| 时长 | num_frames |
|------|-----------|
| ~3 秒 | 81 |
| ~5 秒（默认） | 121 |
| ~10 秒 | 241 |
| ~18 秒（最大） | 441 |

## 3. 功能需求

### 3.1 核心功能

1. **从 CSV 读取批量任务** — 每行一条视频生成任务，支持全部 API 参数
2. **串行提交任务** — 每次只提交一个任务，等待完成后才提交下一个
3. **自动轮询结果** — 提交后定时查询任务状态，直至完成或失败
4. **自动下载视频** — 生成成功后下载视频文件到本地
5. **进度与日志** — 控制台实时显示进度，完整日志记录到文件
6. **异常重试** — 单任务失败自动重试 3 次，仍失败则跳过并记录错误

### 3.2 支持的生成模式

支持 Agnes Video V2.0 的全部模式：

| 模式 | 说明 | 对应参数 |
|------|------|---------|
| Text-to-Video | 纯文本生成视频 | 仅提供 `prompt` |
| Image-to-Video | 单图生成视频 | 提供 `prompt` + `image`（单个 URL） |
| Multi-Image | 多图生成视频 | 提供 `image`（URL 数组） |
| Keyframe | 关键帧动画 | 设置 `extra_body.mode="keyframes"` + `extra_body.image` |

### 3.3 所有可配置的 API 参数

CSV 中每一行都应支持填写以下字段：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `prompt` | string | 否 | — | 视频描述文本 |
| `height` | int | 否 | 768 | 视频高度 |
| `width` | int | 否 | 1152 | 视频宽度 |
| `num_frames` | int | 否 | 121 | 帧数（需满足 8n+1） |
| `frame_rate` | number | 否 | 24 | 帧率 |
| `image` | string | 否 | — | 图片 URL（多图时用 `\|` 分隔） |
| `negative_prompt` | string | 否 | — | 负面提示词 |
| `seed` | int | 否 | — | 随机种子 |
| `mode` | string | 否 | — | `ti2vid` 或 `keyframes` |
| `extra_body_image` | string | 否 | — | 关键帧图片 URLs（`\|` 分隔） |
| `extra_body_mode` | string | 否 | — | 如 `keyframes` |

### 3.4 命令行接口

```bash
python batch_generate.py --csv <input.csv> --output <output_dir> [--key <api_key_file>] [--interval <秒>]
```

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--csv` | 是 | — | 任务 CSV 文件路径 |
| `--output` / `-o` | 否 | `./output` | 视频下载目录 |
| `--key` / `-k` | 否 | `./key.txt` | API Key 文件路径 |
| `--interval` | 否 | `5` | 轮询间隔（秒） |
| `--max-retries` | 否 | `3` | 最大重试次数 |
| `--log` | 否 | `./batch.log` | 日志文件路径 |

### 3.5 CSV 格式要求

- 第一行为表头，字段名与 3.3 节一致
- 可选字段留空即可，工具会自动使用默认值
- 多值字段（图片 URLs）使用 `|` 分隔

示例 `tasks.csv`：

```csv
prompt,width,height,num_frames,frame_rate,seed,image,negative_prompt
A cat walking on beach at sunset,1152,768,121,24,42,,blurry
A robot dancing in rain,1152,768,81,30,,https://example.com/robot.jpg,
Cinematic drone shot over mountains,1920,1080,241,24,,,
```

**各模式 CSV 写法对照：**

| 模式 | `image` 列 | `mode` 列 | `extra_body_image` 列 | `extra_body_mode` 列 |
|------|-----------|-----------|----------------------|---------------------|
| Text-to-Video | 留空 | 留空 | 留空 | 留空 |
| Image-to-Video | 单 URL | 留空 | 留空 | 留空 |
| Multi-Image | URL1\|URL2\|URL3 | 留空 | 留空 | 留空 |
| Keyframe | 留空 | 留空 | URL1\|URL2\|URL3 | keyframes |
| ti2vid 模式 | 单 URL | ti2vid | 留空 | 留空 |

### 3.6 输出规范

- 所有视频下载到 `--output` 指定目录（默认 `./output/`）
- 文件名格式：`{序号4位}_{prompt前20字 sanitized}_{timestamp}.mp4`
- 示例：`0001_A cat walking on bea_20260611_205000.mp4`
- 同时生成一份 `results.csv`，记录每个任务的输入参数、状态、输出文件路径、耗时

## 4. 运行流程

```
读入 CSV
  │
  ▼ 逐行处理
遍历每一行任务
  │
  ├─ ① 校验参数合法性（帧数规则等）
  ├─ ② 调用 POST /v1/videos 提交任务
  ├─ ③ 循环 GET 查询状态（每 interval 秒轮询）
  ├─ ④ 生成成功 → 下载视频到 output 目录
  ├─ ⑤ 生成失败 → 重试（最多 3 次）→ 仍失败则跳过
  │
  ▼ 全部完成
输出 results.csv 汇总报告
```

## 5. 异常处理

| 场景 | 处理方式 |
|------|---------|
| API 返回错误 | 记录错误信息，重试当前任务（最多 3 次） |
| 网络超时/断连 | 等待 10 秒后重试，最多 3 次 |
| 达到最大重试次数 | 跳过当前任务，记录到错误日志，继续下一个 |
| CSV 格式错误 | 立即报错退出，不继续执行 |
| 参数校验失败 | 立即报错退出（如 num_frames 不满足 8n+1） |
| 下载失败 | 重试 2 次，仍失败则记录到 results.csv 中标记为失败 |

## 6. 依赖与环境

- Python ≥ 3.10
- 第三方库：`requests`
- 无需 GPU，纯 CPU 运行（API 调用在云端完成）
- 跨平台支持 Windows / macOS / Linux

## 7. 非功能需求

- 日志同时输出到控制台（彩色）和文件
- 支持 Ctrl+C 优雅中断（已完成的任务不重复）
- 代码符合 `mypy` 和 `ruff` 规范
- 关键函数编写 pytest 单元测试
