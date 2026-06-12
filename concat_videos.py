import subprocess
import os

ffmpeg = r"C:\Users\Administrator\AppData\Local\Programs\Python\Python313\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"

files = sorted([f for f in os.listdir("output") if f.endswith(".mp4") and f.startswith("000")])
print("Files:", files)

with open("concat_list2.txt", "w", encoding="ascii") as f:
    for name in files:
        f.write("file 'output/{}'\n".format(name))

result = subprocess.run(
    [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", "concat_list2.txt",
     "-c", "copy", "output/final_cut.mp4"],
    capture_output=True, text=True,
)

if result.returncode == 0:
    size = os.path.getsize("output/final_cut.mp4")
    print("SUCCESS! final_cut.mp4: {:.1f} MB".format(size / 1e6))
else:
    print("FAILED:", result.stderr[-500:])
