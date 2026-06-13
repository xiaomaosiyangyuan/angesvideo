"""
胶片工坊 v3.2 — 全局统一前缀 + 多帧连续生成 + 帧插值 + 转场

用法:
  # 每镜1张图 + 帧插值补到24fps (默认)
  python film_maker.py --csv film_demo.csv -o film_output --seed 42

  # 每镜24张图/秒 → 直接逐帧播放 (最高连贯性)
  python film_maker.py --csv film_demo.csv -o film_output --seed 42 --frames 24

BGM:  --bgm music.mp3 或 --bgm-url URL
"""
import argparse
import csv
import subprocess
import time
from pathlib import Path

import requests

AGNES_IMAGE_URL = "https://apihub.agnes-ai.com/v1/images/generations"
IMAGE_MODEL = "agnes-image-2.0-flash"
FFMPEG = r"C:\Users\Administrator\AppData\Local\Programs\Python\Python313\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
API_KEY_FILE = r"C:\Users\Administrator\Documents\trae_projects\opencode\anges.txt"


def _img_api(prompt: str, seed: int | None, headers: dict) -> bytes:
    body = {"model": IMAGE_MODEL, "prompt": prompt, "n": 1, "size": "1152x768"}
    if seed is not None:
        body["seed"] = seed
    r = requests.post(AGNES_IMAGE_URL, json=body, headers=headers, timeout=120)
    r.raise_for_status()
    url = r.json()["data"][0]["url"]
    return requests.get(url, timeout=60).content


# ── 步骤1: 生图 ──────────────────────────────────────
def step1_generate(csv_path: str, out_dir: Path, skip: bool, seed: int | None, frames: int) -> list[dict]:
    api_key = open(API_KEY_FILE, encoding="utf-8").readline().strip()
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    global_prefix = ""

    scenes = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = int(row.get("scene", "0"))
            prefix = row.get("prompt_prefix", "")
            suffix = row.get("prompt_suffix", "")
            if prefix and not global_prefix:
                global_prefix = prefix
            full_prompt = f"{global_prefix} {suffix}".strip() if not prefix else f"{prefix} {suffix}".strip()
            scenes.append({
                "id": sid,
                "prompt": full_prompt,
                "duration": int(row.get("duration", "5")),
                "camera": row.get("camera", "static"),
                "subtitle": row.get("subtitle", ""),
            })

    img_dir = out_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    total_imgs = 0

    for s in scenes:
        if frames > 1:
            # 多帧模式：每镜生成 duration × frames 张
            n_per_shot = s["duration"] * frames
            s["frames"] = []
            for fi in range(n_per_shot):
                pct = f"[帧{fi+1}/{n_per_shot} 进度{int((fi+1)/n_per_shot*100)}%]"
                fp = img_dir / f"{s['id']:04d}_{fi:04d}.png"
                s["frames"].append(str(fp))
                if skip and fp.exists():
                    continue
                prompt = f"{s['prompt']} {pct}"
                print(f"  [{s['id']:03d}_{fi:04d}] 生成...", end=" ", flush=True)
                try:
                    data = _img_api(prompt, seed, headers)
                    with open(fp, "wb") as f:
                        f.write(data)
                    print(f"OK ({len(data)//1024}KB)")
                    total_imgs += 1
                    time.sleep(0.5)
                except Exception as e:
                    print(f"失败: {e}")
        else:
            # 单帧模式：每镜1张 + 后续zoompan
            fp = img_dir / f"{s['id']:04d}.png"
            s["image"] = str(fp)
            if skip and Path(fp).exists():
                print(f"  [{s['id']:03d}] 跳过")
                continue
            print(f"  [{s['id']:03d}] 生成...", end=" ", flush=True)
            try:
                data = _img_api(s["prompt"], seed, headers)
                with open(fp, "wb") as f:
                    f.write(data)
                print(f"OK ({len(data)//1024}KB)")
                total_imgs += 1
                time.sleep(1)
            except Exception as e:
                print(f"失败: {e}")

    print(f"  共 {total_imgs} 张")
    return scenes


# ── 步骤2: 合视频 ──────────────────────────────────────
def step2_build(scenes: list[dict], out_dir: Path, fps: int, resolution: str, frames: int) -> Path:
    w, h = map(int, resolution.split("x"))
    cd = out_dir / "clips"
    cd.mkdir(parents=True, exist_ok=True)

    clip_paths = []
    for s in scenes:
        cp = cd / f"clip_{s['id']:04d}.mp4"
        clip_paths.append(cp)
        if cp.exists():
            continue

        dur = s["duration"]

        if frames > 1:
            # 多帧模式：直接序列图片
            flist = cd / f"_flist_{s['id']:04d}.txt"
            with open(flist, "w", encoding="utf-8") as f:
                for fp in s["frames"]:
                    f.write(f"file '{Path(fp).resolve()}'\nduration 1\n")
            # 最后一张重复一次
            with open(flist, "a", encoding="utf-8") as f:
                f.write(f"file '{Path(s['frames'][-1]).resolve()}'\n")

            cmd = [
                FFMPEG, "-y", "-f", "concat", "-safe", "0",
                "-i", str(flist),
                "-vf", f"scale={w}:{h}:flags=lanczos,fps={fps},fade=t=in:d=0.3,fade=t=out:st={dur-0.3}:d=0.3",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-preset", "medium", "-crf", "18",
                str(cp),
            ]
            subprocess.run(cmd, capture_output=True, check=True, encoding="utf-8", errors="replace")
            flist.unlink()
        else:
            # 单帧模式：zoompan + minterpolate + fade
            rate = 0.0005 if s["camera"].startswith("slow_") else 0.001
            n = dur * fps
            cam = s["camera"]
            if cam in ("slow_zoom_in", "zoom_in"):
                vf = f"scale={w}:{h}:flags=lanczos,zoompan=z='min(zoom+{rate},{1.05})':d={n}:s={w}x{h}:fps={fps}"
            elif cam in ("slow_zoom_out", "zoom_out"):
                vf = f"scale={w}:{h}:flags=lanczos,zoompan=z='max(zoom-{rate},{1.0})':d={n}:s={w}x{h}:fps={fps}"
            elif cam == "slow_pan_right":
                sw = int(w * 1.05)
                vf = f"scale={sw}:{h}:flags=lanczos,zoompan=z='{w}/{sw}':x='{sw-w}-{sw-w}*on/{n}':d={n}:s={w}x{h}:fps={fps}"
            elif cam == "slow_pan_left_follow":
                sw = int(w * 1.05)
                vf = f"scale={sw}:{h}:flags=lanczos,zoompan=z='{w}/{sw}':x='{sw-w}*on/{n}':d={n}:s={w}x{h}:fps={fps}"
            elif cam == "slow_zoom_in_behind":
                vf = f"scale={w}:{h}:flags=lanczos,zoompan=z='min(zoom+{rate*1.5},{1.08})':d={n}:s={w}x{h}:fps={fps}"
            elif cam == "medium_zoom_in":
                vf = f"scale={w}:{h}:flags=lanczos,zoompan=z='min(zoom+{rate*1.2},{1.06})':d={n}:s={w}x{h}:fps={fps}"
            else:
                vf = f"scale={w}:{h}:flags=lanczos"
            vf += f",minterpolate=fps={fps}:mi_mode=mci"
            vf += f",fade=t=in:d=0.3,fade=t=out:st={dur-0.3}:d=0.3"

            cmd = [
                FFMPEG, "-y", "-loop", "1", "-i", s["image"],
                "-vf", vf, "-c:v", "libx264", "-t", str(dur),
                "-pix_fmt", "yuv420p", "-r", str(fps),
                "-preset", "medium", "-crf", "18", str(cp),
            ]
            subprocess.run(cmd, capture_output=True, check=True, encoding="utf-8", errors="replace")

    # 拼接（转场淡入淡出）
    if len(clip_paths) == 1:
        final = out_dir / "raw_video.mp4"
        subprocess.run([FFMPEG, "-y", "-i", str(clip_paths[0]), "-c", "copy", str(final)],
                       capture_output=True, check=True)
        return final

    xd = 0.5
    cur = clip_paths[0]
    for nxt in clip_paths[1:]:
        mg = cd / f"_m_{nxt.stem}.mp4"
        # 简化：直接concat（xfade复杂且剪辑时长不准）
        fl = cd / "_c.txt"
        with open(fl, "w") as f:
            f.write(f"file '{cur.resolve()}'\nfile '{nxt.resolve()}'\n")
        subprocess.run([
            FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(fl),
            "-c", "copy", str(mg),
        ], capture_output=True, check=True, encoding="utf-8", errors="replace")
        fl.unlink()
        cur = mg

    final = out_dir / "raw_video.mp4"
    subprocess.run([FFMPEG, "-y", "-i", str(cur), "-c", "copy", str(final)],
                   capture_output=True, check=True)
    return final


# ── 步骤3: BGM ──────────────────────────────────────
def step3_bgm(v: Path, bgm: str, o: Path):
    subprocess.run([
        FFMPEG, "-y", "-i", str(v), "-stream_loop", "-1", "-i", bgm,
        "-filter_complex", "[1:a]volume=0.3[a1];[0:a][a1]amix=inputs=2:duration=first[out]",
        "-map", "0:v", "-map", "[out]", "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-shortest", str(o),
    ], capture_output=True, check=True, encoding="utf-8", errors="replace")


# ── 步骤4: 字幕 ──────────────────────────────────────
def step4_sub(v: Path, scenes: list[dict], o: Path):
    srt = v.parent / "_s.srt"
    t = 0.0
    with open(srt, "w", encoding="utf-8") as f:
        for i, s in enumerate(scenes):
            if not s.get("subtitle"):
                t += s["duration"]
                continue
            end = t + s["duration"]
            f.write(f"{i+1}\n{_ts(t)} --> {_ts(end)}\n{s['subtitle']}\n\n")
            t = end
    subprocess.run([
        FFMPEG, "-y", "-i", str(v), "-i", str(srt),
        "-c", "copy", "-c:s", "mov_text", "-metadata:s:s:0", "language=chi", str(o),
    ], capture_output=True, check=True, encoding="utf-8", errors="replace")
    srt.unlink()


def _ts(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


# ── Main ────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(description="胶片工坊 v3.2")
    p.add_argument("--csv", required=True)
    p.add_argument("--output", "-o", default="./film_output")
    p.add_argument("--bgm")
    p.add_argument("--bgm-url")
    p.add_argument("--fps", type=int, default=24)
    p.add_argument("--resolution", default="1920x1080")
    p.add_argument("--skip-images", action="store_true")
    p.add_argument("--seed", type=int, help="固定种子")
    p.add_argument("--frames", type=int, default=1,
                   help="每秒钟生成图数(1=每镜1张+插值, 24=每秒24张逐帧播放)")
    args = p.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    print("=" * 50)
    print("胶片工坊 v3.2")
    print(f"  模式: {'多帧逐张' if args.frames > 1 else '单帧+插值'} (--frames {args.frames})")
    if args.seed:
        print(f"  种子: --seed {args.seed}")
    print("=" * 50)

    print("\n[1/4] 批量生成图片...")
    scenes = step1_generate(args.csv, out, args.skip_images, args.seed, args.frames)

    print("\n[2/4] 合成视频...")
    raw = step2_build(scenes, out, args.fps, args.resolution, args.frames)
    total = sum(s["duration"] for s in scenes)

    bgm = args.bgm
    if args.bgm_url and not bgm:
        print("\n[3/4] 下载BGM...")
        bgm = str(out / "_bgm.mp3")
        r = requests.get(args.bgm_url, timeout=120)
        with open(bgm, "wb") as f:
            f.write(r.content)

    if bgm:
        print("\n[3/4] 添加BGM...")
        bm = out / "v_bgm.mp4"
        step3_bgm(raw, bgm, bm)
        cur = bm
    else:
        print("\n[3/4] 跳过BGM")
        cur = raw

    if any(s.get("subtitle") for s in scenes):
        print("\n[4/4] 添加字幕...")
        final = out / "final_cut.mp4"
        step4_sub(cur, scenes, final)
    else:
        final = cur

    mb = final.stat().st_size / 1e6
    print(f"\n{'='*50}")
    print(f"[完成] {final.name}  ({total}s, {mb:.1f}MB)")
    print(f"       图片: {sum(len(s.get('frames',[1])) for s in scenes)} 张")
    print("=" * 50)


if __name__ == "__main__":
    main()