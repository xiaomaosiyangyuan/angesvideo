"""第一步：生成统一资产图，所有分镜共用"""
import json
import time
import requests

API_KEY = open(r"C:\Users\Administrator\Documents\trae_projects\opencode\anges.txt", encoding="utf-8").readline().strip()
API_URL = "https://apihub.agnes-ai.com/v1/images/generations"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

ASSETS = {
    "robot": "未来人形机器人，全身银白+黑色机械结构，外露精密零件，胸前LED显示五官，赛博牛仔风格，戴宽檐牛仔帽，正面全身站立，写实风格，8K",
    "robot_side": "未来人形机器人侧面全身，银白机械结构，LED面部，赛博牛仔风格，戴牛仔帽，写实风格，8K",
    "zombie": "丧尸正面全身，腐烂皮肤，外露伤口，浑浊眼球无瞳孔，破旧衣服，步履蹒跚，写实恐怖风格，8K",
    "street": "1960年代原子朋克末日废土街道，荒废汽车和建筑，强烈明暗对比，正午阳光，尘土飞扬，宽银幕构图",
    "gun": "复古左轮手枪特写，金属质感，做旧效果，棕色木柄，写实细节，水平放置，白色背景",
    "indoor": "废弃超市内部，破败货架散落杂物，灰尘漂浮，破碎玻璃窗，光束穿过，末日氛围，广角",
    "sunset": "末日废土夕阳地平线，橙红色天空，荒凉荒漠，破败建筑剪影，原子朋克风格，宽银幕",
    "robot_face": "机器人LED面部特写正面，蓝色发光五官，冷漠表情，精密机械结构，科幻感，写实",
    "zombie_face": "丧尸面部特写，腐烂皮肤纹理清晰，浑浊眼球，张开嘴露出残牙，恐怖写实风格",
    "robot_hand": "机器人手部特写，金属关节，油污，机械手指，赛博风格，微距摄影",
}

results = {}
for name, prompt in ASSETS.items():
    print(f"生成 [{name}] ...", end=" ", flush=True)
    resp = requests.post(API_URL, json={"model": "agnes-image-2.0-flash", "prompt": prompt, "n": 1, "size": "1152x768"}, headers=HEADERS, timeout=120)
    data = resp.json()
    url = data["data"][0]["url"]
    results[name] = url
    print(f"OK → {url[:60]}...")
    time.sleep(2)

with open("assets.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n全部 {len(results)} 张资产图已生成，保存到 assets.json")
for k, v in results.items():
    print(f"  {k}: {v}")
