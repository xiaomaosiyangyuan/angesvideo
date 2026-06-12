import requests
url = "https://storage.googleapis.com/agnes-aigc/aigc/videos/2026/06/12/video_00e004055c7157d18e4acd5613be924e1d0f892fd18b57d8.mp4"
resp = requests.get(url, timeout=60)
ct = resp.headers.get("content-type", "")
print(f"Status: {resp.status_code}, Size: {len(resp.content)} bytes, Type: {ct}")
with open("api_test_output.mp4", "wb") as f:
    f.write(resp.content)
print("Downloaded to api_test_output.mp4")