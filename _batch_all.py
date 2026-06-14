"""批量处理全部20章: 统一参考图+图生视频+字幕+TTS配音"""
import asyncio, csv, json, os, subprocess, sys, time
from pathlib import Path

FFMPEG = r"C:\Users\Administrator\AppData\Local\Programs\Python\Python313\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
API = "https://apihub.agnes-ai.com/v1/images/generations"
KEY = open(r"C:\Users\Administrator\Documents\trae_projects\opencode\anges.txt", encoding="utf-8").readline().strip()
SEED = 42

def gen_canonical_images():
    """生成统一参考图(仅首次运行)"""
    assets_file = "doc/assets/urls.json"
    if os.path.exists(assets_file) and os.path.getsize(assets_file) > 100:
        print("参考图已存在,跳过生成")
        with open(assets_file) as f:
            return json.load(f)

    import requests
    os.makedirs("doc/assets", exist_ok=True)
    HEADERS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

    prompts = {
        "lin_chen": "电影级科幻摄影，8K超清。统一主角：天才科学家林晨（45岁，黑发微白，深蓝色科学院长袍，戴全息数据眼镜，睿智沉稳）。林晨正面半身肖像",
        "starship_interior": "星际飞船核心控制室，全息屏幕环绕，蓝色冷光，金属舱壁，中央船长座椅，科幻感",
        "space_debris": "深邃星空背景，远处银河旋臂，无数恒星闪烁，星云色彩斑斓，史诗太空场景",
        "earth_explosion": "地球从内部爆炸解体，炽热岩浆从裂缝喷涌，橙红强光撕裂星球，碎片飞散",
    }

    urls = {}
    for name, prompt in prompts.items():
        body = {"model": "agnes-image-2.0-flash", "prompt": prompt, "n": 1, "size": "1152x768", "seed": SEED}
        r = requests.post(API, json=body, headers=HEADERS, timeout=120)
        url = r.json()["data"][0]["url"]
        urls[name] = url
        img = requests.get(url, timeout=60).content
        with open(f"doc/assets/{name}.png", "wb") as f:
            f.write(img)
        print(f"  [{name}] OK {len(img)//1024}KB")
        time.sleep(1)

    with open(assets_file, "w") as f:
        json.dump(urls, f)
    return urls

def classify_shot(prompt):
    """根据分镜文本判断用哪张参考图"""
    p = prompt
    if any(k in p for k in ["林晨", "科学家", "博士", "人物", "主角"]):
        return "lin_chen"
    if any(k in p for k in ["控制", "驾驶", "舱室", "内部", "屏幕", "数据", "飞船内"]):
        return "starship_interior"
    if any(k in p for k in ["爆炸", "地球", "岩浆", "裂缝", "毁灭", "解体"]):
        return "earth_explosion"
    return "space_debris"

def process_chapter(ch_num, urls):
    """处理单个章节"""
    out_dir = f"chapter{ch_num}_output"
    if os.path.exists(f"{out_dir}/chapter{ch_num}_final.mp4"):
        print(f"  [章{ch_num}] 已有输出,跳过")
        return

    # 1. 生成固定image的CSV
    csv_in = f"doc/chapter{ch_num}_60shots.csv"
    csv_out = f"_ch{ch_num}_fixed.csv"
    with open(csv_in, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    with open(csv_out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["prompt", "image", "num_frames", "frame_rate", "seed"])
        for row in rows:
            img_key = classify_shot(row["prompt"])
            w.writerow([row["prompt"], urls[img_key], row.get("num_frames",81), row.get("frame_rate",24), SEED])

    # 2. 跑batch_generate
    cmd = f'python batch_generate.py --csv {csv_out} -o {out_dir} --key "C:\\Users\\Administrator\\Documents\\trae_projects\\opencode\\anges.txt" --log ch{ch_num}.log --parallel --concat --concat-name chapter{ch_num}_final.mp4'
    print(f"  [章{ch_num}] 生成视频...")
    ret = os.system(cmd)
    if ret != 0:
        print(f"  [章{ch_num}] 视频生成失败!")
        return

    # 3. 字幕用CSV的prompt字段自动生成
    srt_path = f"{out_dir}/_subtitles.srt"
    tc = 0.0
    with open(csv_out, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, row in enumerate(rows):
            dur = int(row.get("num_frames",81)) / int(row.get("frame_rate",24))
            end = tc + dur
            text = row["prompt"][:60]
            def ts(sec):
                h = int(sec//3600); m = int((sec%3600)//60); s = sec%60
                return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".",",")
            f.write(f"{i+1}\n{ts(tc)} --> {ts(end)}\n{text}\n\n")
            tc = end

    # 4. 字幕混入视频
    video = f"{out_dir}/chapter{ch_num}_final.mp4"
    if os.path.exists(video):
        tmp = video + ".tmp"
        subprocess.run([FFMPEG, "-y", "-i", video, "-i", srt_path,
            "-c", "copy", "-c:s", "mov_text", "-metadata:s:s:0", "language=chi", tmp],
            capture_output=True, check=True, encoding="utf-8", errors="replace")
        os.replace(tmp, video)
        print(f"  [章{ch_num}] 字幕已混入")
    os.remove(srt_path)

    # 5. TTS配音(异步)
    async def do_tts():
        audio_dir = Path(f"{out_dir}/_audio")
        audio_dir.mkdir(parents=True, exist_ok=True)
        from edge_tts import Communicate
        all_audio = []
        tc = 0.0
        for i, row in enumerate(rows):
            dur = int(row.get("num_frames",81)) / int(row.get("frame_rate",24))
            text = row["prompt"][:80]
            if not text.strip():
                tc += dur; continue
            ap = audio_dir / f"{i:04d}.mp3"
            if not ap.exists():
                await Communicate(text, "zh-CN-XiaoxiaoNeural").save(str(ap))
            padded = audio_dir / f"{i:04d}_p.mp3"
            if not padded.exists():
                subprocess.run([FFMPEG, "-y", "-i", str(ap),
                    "-af", f"atempo=1.0,apad=pad_dur={dur}", "-t", str(dur),
                    "-c:a", "mp3", "-b:a", "192k", str(padded)],
                    capture_output=True, check=True, encoding="utf-8", errors="replace")
            all_audio.append(str(padded))
            tc += dur

        # 拼接配音
        inputs = []
        for f in all_audio:
            inputs.extend(["-i", f])
        n = len(all_audio)
        if n == 0: return
        filter_str = "".join(f"[{i}:a]" for i in range(n)) + f"concat=n={n}:v=0:a=1[out]"
        subprocess.run([FFMPEG, "-y"] + inputs + ["-filter_complex", filter_str,
            "-map", "[out]", f"{out_dir}/_voiceover.mp3"],
            check=True, capture_output=True, encoding="utf-8", errors="replace")

        # 混入视频
        subprocess.run([FFMPEG, "-y", "-i", video, "-i", f"{out_dir}/_voiceover.mp3",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", video+".vo"],
            check=True, capture_output=True, encoding="utf-8", errors="replace")
        os.replace(video+".vo", video)
        print(f"  [章{ch_num}] 配音已混入")

    asyncio.run(do_tts())
    print(f"  [章{ch_num}] 完成! {video}")

    # 清理临时文件
    os.remove(csv_out)
    import shutil
    shutil.rmtree(f"{out_dir}/_audio", ignore_errors=True)
    for f in Path(out_dir).glob("_voiceover*"):
        f.unlink(missing_ok=True)
    for f in Path(out_dir).glob("_xfade_*"):
        f.unlink(missing_ok=True)


# ===== MAIN =====
print("=" * 50)
print("批量处理 重生之超级战舰 全部20章")
print("=" * 50)

# Step 1: 统一参考图
print("\n[0/20] 生成统一参考图...")
urls = gen_canonical_images()
for k, v in urls.items():
    print(f"  {k}: {v[:50]}...")

# Step 2: 逐章处理
for ch in range(1, 21):
    csv_path = f"doc/chapter{ch}_60shots.csv"
    if not os.path.exists(csv_path):
        print(f"\n[章{ch}] CSV不存在,跳过")
        continue
    print(f"\n[{ch}/20] 处理第{ch}章...")
    process_chapter(ch, urls)

print("\n" + "=" * 50)
print("全部完成!")
print("=" * 50)
