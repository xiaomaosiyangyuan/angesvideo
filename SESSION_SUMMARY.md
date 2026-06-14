# angesvideo 项目状态总结

## 项目概览
Agnes Video V2.0 批量视频生成工具 + 《重生之超级战舰》AI短剧制作

---

## 已完成功能

### 核心工具链（v1.0 - v5.0）

| 版本 | 功能 | 状态 |
|------|------|------|
| v1.0.0 | 基础批量视频生成(CSV→API→下载) | ✅ |
| v1.1.0 | image_prompt 一步式文生图→图生视频 | ✅ |
| v2.0.0 | 多资产批量生成(image_prompts) | ✅ |
| v2.2.0 | 自动关键帧动画(keyframes) | ✅ |
| v3.0.0 | film_maker.py 胶片工坊(文生图→KenBurns→BGM→字幕) | ✅ |
| v3.2.0 | 多帧连续生成(--frames N) | ✅ |
| v4.0.0 | 并行模式(--parallel) + 24fps合规 | ✅ |
| v5.0.0 | 线程池并行提交 + subtitle字段 | ✅ |

### 当前工作流（推荐）

```bash
# 方案A: 视频API生成 (快, 质量中等)
python batch_generate.py --csv doc/chapterN_60shots.csv -o chapterN_output --parallel --concat

# 方案B: 文生图+KenBurns (慢, 高清)
python film_maker.py --csv film_demo.csv -o output --seed 42 --bgm-url URL
```

---

## 关键配置

### 统一角色参考图
- seed=42 固定
- 4张标准图: lin_chen, starship_interior, space_debris, earth_explosion
- 存储在 `doc/assets/urls.json`
- 每章生成前先运行 `_batch_all.py` 中的 `gen_canonical_images()`

### CSV格式
```csv
prompt,image,num_frames,frame_rate,seed
"分镜描述","参考图URL",81,24,42
```
- 使用 `image` 列传参考图URL（不换脸）
- 每镜81帧@24fps=3.4秒, 60镜=3分22秒
- 字幕由 batch_generate.py 自动生成

### 并行参数
```bash
--parallel      # 60镜同时提交(非逐镜等待)
--concat        # 自动拼接(简单-c copy, 不用xfade)
--concat-name   # 输出文件名
```

---

## 已生成的章节

| 章节 | 输出目录 | 大小 | 时长 | 状态 |
|------|---------|------|------|------|
| 第1章 | chapter1_output | 66 MB | 3:22 | ✅ 含字幕 |
| 第2章 | chapter2_output | 67 MB | 3:22 | ✅ 含字幕 |
| 第3-50章 | — | — | — | ⏳ 待生成 |

### doc/下的CSV
- chapter1_60shots.csv ~ chapter50_60shots.csv
- 每章60镜, 列: prompt, image_prompt, width, height, num_frames, frame_rate, seed, negative_prompt
- 需用 _batch_all.py 的 process_chapter() 处理

---

## 代码关键文件

### 核心模块
- `batch_generate.py` — 主入口
- `cli.py` — 命令行参数(--parallel, --concat, --csv等)
- `reader.py` — CSV读取(支持utf-8-sig BOM)
- `validator.py` — 参数校验(8n+1帧数规则等)
- `api_client.py` — API调用(agnes-image + agnes-video)
- `runner.py` — 执行引擎(串行/并行/生图/轮询/下载/拼接)
- `reporter.py` — 结果输出
- `_types.py` — 数据类(TaskConfig含subtitle字段)
- `_constants.py` — 常量(FFMPEG路径, 模型ID等)

### 辅助脚本
- `_batch_all.py` — 批量处理全部章节(含统一参考图生成)
- `film_maker.py` — 胶片工坊(文生图→KenBurns→BGM→字幕)
- `generate_assets.py` — 生成统一参考图

### doc/目录
- `chapterN_60shots.csv` — 各章节分镜CSV
- `assets/urls.json` — 统一参考图URL
- `重生之超级战舰.txt` — 原著小说

---

## 注意事项

### 不要做的事情
- ❌ 不要手动删除 chapter*_output 目录下的视频文件
- ❌ 不要在 git commit 时清理 mp4 文件(已配LFS)
- ❌ 不要在 _batch_all.py 中二次混入字幕(会报错但无害)

### 已知问题
1. **视频只有几秒**: _concat_videos_simple 中的文件名正则 `re.match(r"\d{4}", name)` 已在 fix 中修正
2. **副字幕混入失败**: batch_generate.py 已自动混入字幕, _batch_all.py 二次混入会报错
3. **角色换脸**: 必须用 `image` 列传固定URL, 不能用 `image_prompt` 每次都生

### 剩余工作
- 处理第3-50章: 运行 `python -c "import _batch_all; _batch_all.process_chapter(N, urls)"`
- edge-tts配音: 当前 batch_generate 只加字幕不加配音, 需单独跑TTS脚本
- BGM: 使用 `--bgm-url` 参数, 推荐 Pixabay Music

---

## 版本标签
- v1.0.0 ~ v5.0.0 已推送到 GitHub
- 仓库: https://github.com/xiaomaosiyangyuan/angesvideo
