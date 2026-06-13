"""
胶片工坊 — 批量生图 → 运镜合成 → 加BGM → 加字幕

用法:
  python film_maker.py --csv film_demo.csv --output film_output
  
  可选:
    --bgm music.mp3      本地BGM文件
    --bgm-url URL        在线BGM地址（自动下载）
    --fps 24             帧率(默认24)
    --resolution 1920x1080  分辨率(默认1920x1080)
    --skip-images        跳过出图(直接复用已有图片)

BGM免费资源(商用可):
  - Pixabay Music:    https://pixabay.com/music/
  - DOVA-SYNDROME:    https://dova-s.jp
  - Mixkit:           https://mixkit.co/free-stock-music/
  - 魔王魂:           https://maou.audio
  - YouTube Audio Lib:https://www.youtube.com/audiolibrary
"""
import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

# ── 常量 ──────────────────────────────────────────────
AGNES_IMAGE_URL = "https://apihub.agnes-ai.com/v1/images/generations"
IMAGE_MODEL = "agnes-image-2.0-flash"
FFMPEG = r"C:\Users\Administrator\AppData\Local\Programs\Python\Python313\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
API_KEY_FILE = r"C:\Users\Administrator\Documents\trae_projects\opencode\anges.txt"

# ── Ken Burns 运镜 → FFmpeg zoompan 参数 ──────────────
def _zoompan_expr(camera: str, duration: int, fps: int, w: int, h: int) -> str:
    n_frames = duration * fps
    zoom_step = 0.001
    if camera == "zoom_in":
        return f"scale={w}:{h}:flags=lanczos,zoompan=z='min(zoom+{zoom_step},{1.05})':d={n_frames}:s={w}x{h}:fps={fps}"
    elif camera == "zoom_out":
        return f"scale={w}:{h}:flags=lanczos,zoompan=z='max(zoom-{zoom_step},{1.0})':d={n_frames}:s={w}x{h}:fps={fps}"
    elif camera == "pan_right":
        return f"scale={int(w*1.05)}:{int(h*1.05)}:flags=lanczos,zoompan=z='{w}/{int(w*1.05)}':x='{int(w*0.05)}-{int(w*0.05)}*on/{n_frames}':d={n_frames}:s={w}x{h}:fps={fps}"
    elif camera == "pan_left":
        return f"scale={int(w*1.05)}:{int(h*1.05)}:flags=lanczos,zoompan=z='{w}/{int(w*1.05)}':x='{int(w*0.05)}*on/{n_frames}':d={n_frames}:s={w}x{h}:fps={fps}"
    else:
        return f"scale={w}:{h}:flags=lanczos"


# ── 步骤1: 批量生图 ─────────────────────────────────
def step1_generate_images(csv_path: str, output_dir: Path, skip: bool = False) -> list[dict]:
    """读取CSV，逐行生成图片，返回场景列表"""
    import requests

    api_key = open(API_KEY_FILE, encoding="utf-8").readline().strip()
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    scenes = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = int(row.get("scene", "0"))
            prompt = row.get("prompt", "")
            duration = int(row.get("duration", "5"))
            camera = row.get("camera", "static")
            subtitle = row.get("subtitle", "")
            scenes.append({"id": sid, "prompt": prompt, "duration": duration,
                           "camera": camera, "subtitle": subtitle})

    img_dir = output_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    for s in scenes:
        img_path = img_dir / f"{s['id']:04d}.png"
        s["image"] = str(img_path)

        if skip and img_path.exists():
            print(f"  [{s['id']:03d}] 跳过（已存在）")
            continue

        print(f"  [{s['id']:03d}] 生成: {s['prompt'][:40]}...", end=" ", flush=True)
        resp = requests.post(
            AGNES_IMAGE_URL,
            json={"model": IMAGE_MODEL, "prompt": s["prompt"], "n": 1, "size": "1152x768"},
            headers=headers, timeout=120,
        )
        if not resp.ok:
            print(f"失败: {resp.text[:100]}")
            continue
        url = resp.json()["data"][0]["url"]

        # 下载图片
        img_resp = requests.get(url, timeout=60)
        with open(img_path, "wb") as f:
            f.write(img_resp.content)
        print(f"OK ({len(img_resp.content)//1024}KB)")

        time.sleep(1)

    return scenes


# ── 步骤2: 合成视频（Ken Burns + 过渡）───────────────
def step2_build_video(scenes: list[dict], output_dir: Path, fps: int, resolution: str) -> Path:
    """用FFmpeg逐段合成 + 拼接成最终视频"""
    w, h = map(int, resolution.split("x"))
    clips_dir = output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    clip_files = []

    for s in scenes:
        out_clip = clips_dir / f"clip_{s['id']:04d}.mp4"
        clip_files.append(out_clip)

        if out_clip.exists():
            continue

        vf = _zoompan_expr(s["camera"], s["duration"], fps, w, h)
        input_img = str(s["image"])

        cmd = [
            FFMPEG, "-y", "-loop", "1", "-i", input_img,
            "-vf", vf,
            "-c:v", "libx264", "-t", str(s["duration"]),
            "-pix_fmt", "yuv420p", "-r", str(fps),
            "-preset", "medium", "-crf", "18",
            str(out_clip),
        ]
        subprocess.run(cmd, capture_output=True, check=True, encoding="utf-8", errors="replace")

    # 合成过渡
    if len(clip_files) == 1:
        final = output_dir / "raw_video.mp4"
        cmd = [FFMPEG, "-y", "-i", str(clip_files[0]), "-c", "copy", str(final)]
        subprocess.run(cmd, capture_output=True, check=True)
        return final

    concat_path = output_dir / "_concat.txt"
    with open(concat_path, "w", encoding="utf-8") as f:
        for c in clip_files:
            f.write(f"file '{c.resolve()}'\n")

    final_raw = output_dir / "raw_video.mp4"
    cmd = [
        FFMPEG, "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_path),
        "-c", "copy", str(final_raw),
    ]
    subprocess.run(cmd, capture_output=True, check=True, encoding="utf-8", errors="replace")
    concat_path.unlink()

    return final_raw


# ── 步骤3: 加BGM ────────────────────────────────────
def step3_add_bgm(video_path: Path, bgm_path: str, output_path: Path):
    """混入背景音乐，按视频时长循环/裁剪"""
    cmd = [
        FFMPEG, "-y",
        "-i", str(video_path),
        "-stream_loop", "-1", "-i", bgm_path,
        "-filter_complex",
        "[1:a]volume=0.3[a1];[0:a][a1]amix=inputs=2:duration=first[out]",
        "-map", "0:v", "-map", "[out]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(output_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True, encoding="utf-8", errors="replace")


# ── 步骤4: 加字幕 ────────────────────────────────────
def step4_add_subtitles(video_path: Path, scenes: list[dict], output_path: Path, font: str = "SimSun"):
    """生成SRT字幕文件并用FFmpeg混入字幕流"""
    srt_path = video_path.parent / "_subtitles.srt"
    with open(srt_path, "w", encoding="utf-8") as f:
        time_cursor = 0.0
        for i, s in enumerate(scenes):
            if not s.get("subtitle"):
                time_cursor += s["duration"]
                continue
            start = time_cursor
            end = time_cursor + s["duration"]
            f.write(f"{i+1}\n")
            f.write(f"{_srt_time(start)} --> {_srt_time(end)}\n")
            f.write(f"{s['subtitle']}\n\n")
            time_cursor = end

    cmd = [
        FFMPEG, "-y",
        "-i", str(video_path),
        "-i", str(srt_path),
        "-c", "copy",
        "-c:s", "mov_text",
        "-metadata:s:s:0", "language=chi",
        str(output_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True, encoding="utf-8", errors="replace")
    srt_path.unlink()


def _srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


# ── 主流程 ───────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="胶片工坊 — 批量生图→运镜合成→加BGM→加字幕")
    parser.add_argument("--csv", required=True, help="故事板CSV")
    parser.add_argument("--output", "-o", default="./film_output", help="输出目录")
    parser.add_argument("--bgm", help="背景音乐文件路径")
    parser.add_argument("--bgm-url", help="在线BGM地址(自动下载)")
    parser.add_argument("--fps", type=int, default=24, help="帧率")
    parser.add_argument("--resolution", default="1920x1080", help="分辨率(默认1920x1080)")
    parser.add_argument("--sub-font", default="SimSun", help="字幕字体")
    parser.add_argument("--skip-images", action="store_true", help="跳过出图(复用已有)")
    args = parser.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    print("=" * 50)
    print("胶片工坊 v1.0")
    print("=" * 50)

    # Step 1: 批量出图
    print("\n[Step 1/4] 批量生成图片...")
    scenes = step1_generate_images(args.csv, out, args.skip_images)
    print(f"  完成: {len(scenes)} 张")

    # Step 2: 合成视频
    print("\n[Step 2/4] 合成视频（Ken Burns 运镜）...")
    raw_video = step2_build_video(scenes, out, args.fps, args.resolution)
    total_sec = sum(s["duration"] for s in scenes)
    print(f"  完成: {raw_video.name} ({total_sec}s)")

    # Step 3: 加BGM
    bgm_path = args.bgm
    if args.bgm_url and not bgm_path:
        import requests
        print(f"\n[Step 3/4] 下载BGM...")
        bgm_path = str(out / "_bgm.mp3")
        resp = requests.get(args.bgm_url, timeout=120)
        with open(bgm_path, "wb") as f:
            f.write(resp.content)
        print(f"  BGM下载完成 ({len(resp.content)//1024}KB)")

    if bgm_path:
        print("\n[Step 3/4] 添加背景音乐...")
        bgm_video = out / "video_with_bgm.mp4"
        step3_add_bgm(raw_video, bgm_path, bgm_video)
        print(f"  完成: {bgm_video.name}")
        current = bgm_video
    else:
        print("\n[Step 3/4] 跳过（无BGM）")
        current = raw_video

    # Step 4: 加字幕
    has_sub = any(s.get("subtitle") for s in scenes)
    if has_sub:
        print("\n[Step 4/4] 添加字幕...")
        final = out / "final_cut.mp4"
        step4_add_subtitles(current, scenes, final, args.sub_font)
        print(f"  完成: {final.name}")
    else:
        print("\n[Step 4/4] 跳过（无字幕）")
        final = current

    # 统计
    size_mb = final.stat().st_size / 1e6
    print("\n" + "=" * 50)
    print("[完成] 全部完成!")
    print(f"   输出: {final}")
    print(f"   时长: {total_sec}s ({total_sec/60:.1f}分钟)")
    print(f"   大小: {size_mb:.1f} MB")
    print(f"   图片: {len(scenes)} 张")
    print("=" * 50)


if __name__ == "__main__":
    main()