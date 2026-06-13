"""快速下载免费商用BGM"""
import requests, json

API = "https://pixabay.com/api/v1/search/music/"
params = {"q": "cinematic dark suspense", "per_page": 5}
r = requests.get(API, params=params, timeout=15)
data = r.json()

for hit in data.get("hits", []):
    title = hit.get("title", "?")
    print(f"  [{title}]")
    dl = hit.get("audiodownload")
    if dl:
        resp = requests.get(dl, timeout=60)
        path = f"bgm_{title[:20]}.mp3".replace("/","_")
        with open(path, "wb") as f:
            f.write(resp.content)
        print(f"    DOWNLOADED → {path} ({len(resp.content)//1024}KB)")
        break
    else:
        print(f"    no download link")
