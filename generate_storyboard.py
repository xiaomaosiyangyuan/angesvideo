"""生成丧尸清道夫 10 分钟故事板 CSV（120 分镜）"""
import csv

BASE_ASSETS = {
    "robot": "未来人形机器人，全身银白+黑色机械结构，外露精密零件，胸前LED显示五官，赛博牛仔风格，戴宽檐牛仔帽",
    "zombie": "丧尸，腐烂皮肤，外露伤口，浑浊眼球无瞳孔，破旧衣服，步履蹒跚，面目狰狞",
    "street": "1960年代原子朋克风格末日废土街道，荒废汽车和建筑，强烈明暗对比，正午阳光，尘土飞扬",
    "gun": "复古左轮手枪特写，金属质感，做旧效果，写实细节，枪管冒烟",
    "indoor": "废弃商店内部，破败货架，灰尘，破碎玻璃窗，光束穿过，末日氛围",
    "sunset": "末日废土夕阳天空，橙红色，荒凉地平线，破败建筑剪影，原子朋克风格",
    "robot_face": "机器人LED面部特写，发光五官，冷漠表情，精密机械结构，科幻感",
    "zombie_close": "丧尸面部特写，腐烂皮肤纹理清晰，浑浊眼球，张开嘴露出残牙，恐怖",
    "robot_hand": "机器人手部机械结构特写，金属关节，油污，握枪姿势，赛博风格",
}

SHOTS = [
    # ===== 第一幕：抵达 (Arrival) =====
    # 1-15: 开车进入废土小镇
    (1, "大远景，荒漠中一条废弃公路延伸向远方的原子朋克小镇，热浪扭曲空气，寂静无声", ["robot", "street", "sunset"]),
    (2, "远景跟拍，一辆改装越野车在荒漠公路上行驶，扬起尘土，镜头跟随车辆平移", ["robot", "street", "sunset"]),
    (3, "中景车内，机器人清道夫手握方向盘，LED面部显示专注表情，车内仪表盘闪烁", ["robot", "robot_face", "gun"]),
    (4, "主观视角，透过挡风玻璃看小镇越来越近，破败建筑轮廓清晰，风滚草吹过路面", ["robot", "street", "sunset"]),
    (5, "特写机器人手部操作换挡，机械关节精确运动，金属手指敲击档杆", ["robot_hand", "robot", "gun"]),
    (6, "远景低角度，车辆驶过倒在路边的路牌\"NEW HAVEN - POP 0\"，镜头仰拍", ["robot", "street", "zombie"]),
    (7, "中景侧面，车辆经过废弃加油站，破碎玻璃，锈蚀油泵，快速闪过", ["robot", "street", "indoor"]),
    (8, "车载镜头，车辆减速驶入主街道，两旁荒废店面，风吹报纸飘过路面", ["robot", "street", "zombie"]),
    (9, "全景，车辆停在街道中央，引擎熄火，蒸汽从引擎盖冒出，镜头环绕", ["robot", "street", "gun"]),
    (10, "特写车门打开，机械靴子踩在沥青路面上，激起一小片尘土", ["robot_hand", "robot", "street"]),
    (11, "中低角度，机器人从车里站起，全景展示全身造型，LED面部扫描四周", ["robot", "robot_face", "street"]),
    (12, "360度环绕镜头，机器人站在车旁观察环境，手放在枪套上，缓慢转身", ["robot", "street", "gun"]),
    (13, "特写LED面部表情变化：从冷漠切换到警惕，蓝色光芒微微闪烁", ["robot_face", "robot", "zombie"]),
    (14, "中景，机器人走向车头，检查引擎盖下冒出的蒸汽，环境音寂静", ["robot", "robot_hand", "street"]),
    (15, "远景高角度，展示小镇全貌：机器人、车辆、废弃街道，构图居中", ["robot", "street", "sunset"]),

    # ===== 第二幕：探索 (Exploration) =====
    # 16-35: 搜索物资
    (16, "中景跟拍，机器人沿街道行走，左右观察，镜头缓慢平移", ["robot", "street", "gun"]),
    (17, "机器人停在废弃超市前，LED显示思考表情，看招牌\"GENERAL STORE\"", ["robot", "street", "indoor"]),
    (18, "特写手部推开门，门铰链发出刺耳声，裂缝透光", ["robot_hand", "robot", "indoor"]),
    (19, "中景推镜头进入超市内部，镜头从昏暗到微亮，货架倒塌散落杂物", ["indoor", "robot", "street"]),
    (20, "机器人走过货架，手指扫过灰尘覆盖的罐头，LED闪烁", ["robot", "robot_hand", "indoor"]),
    (21, "特写罐头标贴\"1957 - BEANS\"，机器人手指拿起罐头检查", ["robot_hand", "indoor", "gun"]),
    (22, "中景，机器人将罐头装入背包，继续搜索，镜头跟拍", ["robot", "indoor", "robot_face"]),
    (23, "突然远处传来撞击声，机器人立刻停住，LED切换为警觉", ["robot_face", "robot", "indoor"]),
    (24, "特写耳朵（机械听觉传感器）微微转动，捕捉声音方向", ["robot", "robot_hand", "indoor"]),
    (25, "中景，机器人缓慢转身，手部移向枪套，凝视超市深处", ["robot", "gun", "zombie"]),
    (26, "主观视角透过倒塌货架看向黑暗中的门道，紧张氛围", ["indoor", "zombie", "robot"]),
    (27, "机器人向前缓慢移动，靴子踩在碎玻璃上发出声响，特写脚步", ["robot", "robot_hand", "indoor"]),
    (28, "中景，机器人到达内部门口，侧身倾听，手按在枪上", ["robot", "gun", "robot_face"]),
    (29, "推开门进入仓库区，昏暗光线，天花板漏水形成水坑", ["indoor", "robot", "gun"]),
    (30, "中景，机器人搜索仓库货架，找到弹药箱，LED显示满意", ["robot", "robot_face", "gun"]),
    (31, "特写手指打开弹药箱，看到一排整齐的左轮手枪子弹", ["robot_hand", "gun", "robot"]),
    (32, "机器人取出一排子弹，放入背包，动作精准流畅", ["robot", "robot_hand", "gun"]),
    (33, "外面传来第二声撞击，比上次更大，玻璃震碎的声音", ["robot_face", "zombie", "indoor"]),
    (34, "中景，机器人快速起身，背起包，快步走向门口", ["robot", "gun", "indoor"]),
    (35, "在门口停住，向外观察，街道上出现一个跌跌撞撞的人影", ["zombie", "street", "robot"]),

    # ===== 第三幕：遭遇 (Encounter) =====
    # 36-55: 丧尸出现，紧张升级
    (36, "远景，丧尸从街道拐角出现，步履蹒跚，衣衫褴褛", ["zombie", "street", "robot"]),
    (37, "中景，机器人从门缝观察，LED表情凝重，评估威胁", ["robot_face", "robot", "zombie"]),
    (38, "丧尸缓慢走近，发出低沉的嘶吼声，镜头推近脸部特写", ["zombie_close", "zombie", "street"]),
    (39, "特写，丧尸浑浊眼球，外露牙齿，腐烂皮肤细节清晰", ["zombie_close", "zombie", "street"]),
    (40, "中景，机器人决定离开超市，从侧门悄声退出", ["robot", "indoor", "gun"]),
    (41, "机器人沿建筑阴影移动，避开丧尸视线，战术动作", ["robot", "street", "zombie"]),
    (42, "主观视角，从拐角偷看丧尸在街道上徘徊", ["zombie", "street", "gun"]),
    (43, "特写手部解开枪套扣子，缓慢拔枪，金属摩擦声", ["robot_hand", "gun", "robot"]),
    (44, "突然另一只丧尸从侧面出现，机器人扭头发现", ["zombie", "robot", "street"]),
    (45, "中景快速反应，机器人转身面对两只丧尸，举枪", ["robot", "gun", "zombie"]),
    (46, "丧尸发现机器人，加速冲来，发出尖锐嚎叫", ["zombie_close", "zombie", "robot"]),
    (47, "特写LED面部切换到战斗模式：红色光芒，冷酷表情", ["robot_face", "robot", "zombie"]),
    (48, "中景，机器人扣动扳机，枪口火焰喷出，镜头震动", ["gun", "robot", "zombie"]),
    (49, "慢动作特写，子弹穿过空气，击中丧尸胸口，血花飞溅", ["zombie_close", "gun", "zombie"]),
    (50, "中景，丧尸中弹后仰倒下，尘土飞扬", ["zombie", "street", "gun"]),
    (51, "快速转向另一只丧尸，再开一枪，命中头部", ["gun", "zombie", "robot"]),
    (52, "特写，第二只丧尸头部中弹，倒地抽搐后静止", ["zombie_close", "zombie", "street"]),
    (53, "中景，机器人保持射击姿势，缓慢扫视四周", ["robot", "gun", "robot_face"]),
    (54, "等待数秒确认无更多威胁，LED切换回正常模式", ["robot_face", "robot", "street"]),
    (55, "机器人走近尸体踢了一脚确认死亡，俯身检查", ["robot", "zombie", "gun"]),

    # ===== 第四幕：群战 (Combat) =====
    # 56-85: 丧尸群出现，大规模战斗
    (56, "远景，街道尽头出现一大群丧尸，至少20只，缓慢涌来", ["zombie", "street", "robot"]),
    (57, "中景，机器人后退一步，评估形势，快速检查弹药", ["robot", "gun", "robot_face"]),
    (58, "特写手指打开左轮弹仓检查子弹数，然后合上", ["robot_hand", "gun", "robot"]),
    (59, "中景，机器人冲向附近建筑二楼的楼梯，快速攀爬", ["robot", "street", "indoor"]),
    (60, "俯拍，丧尸群涌向建筑下方，爬上楼梯，场面混乱", ["zombie", "street", "robot"]),
    (61, "机器人到达二楼平台，俯视下方丧尸群，举枪射击", ["robot", "gun", "zombie"]),
    (62, "俯拍中景，连续射击，每一枪打倒一个丧尸", ["gun", "zombie", "robot"]),
    (63, "特写弹壳弹跳落地，左轮手枪冒烟", ["gun", "robot_hand", "robot"]),
    (64, "中景，丧尸爬上一楼开始上楼梯，镜头跟拍", ["zombie", "indoor", "robot"]),
    (65, "机器人踢倒楼梯，丧尸摔落，继续射击", ["robot", "zombie", "gun"]),
    (66, "特写手部快速换弹，弹壳掉落，新弹装入", ["robot_hand", "gun", "robot"]),
    (67, "丧尸突破其他楼梯口冲上二楼，机器人后退", ["zombie", "indoor", "robot"]),
    (68, "中景近距格斗，机器人用枪托砸向丧尸头部", ["robot", "zombie", "gun"]),
    (69, "特写枪托砸中丧尸脸部，血肉模糊", ["zombie_close", "gun", "robot"]),
    (70, "转身一脚踢飞另一只丧尸，机械腿部特写", ["robot", "zombie", "robot_hand"]),
    (71, "中景搏斗，机器人抓住丧尸手臂扭断，动作流畅", ["robot", "zombie", "robot_hand"]),
    (72, "机器人掏出手枪继续射击，再次命中", ["gun", "robot", "zombie"]),
    (73, "全景二楼平台，地上躺满了丧尸尸体，机器人喘气", ["robot", "zombie", "indoor"]),
    (74, "LED面部显示呼吸急促的数据动画，快速闪烁", ["robot_face", "robot", "zombie"]),
    (75, "楼下还有丧尸涌来，机器人环顾四周寻找出路", ["robot", "zombie", "street"]),
    (76, "向建筑后方移动，看到消防逃生梯", ["robot", "indoor", "street"]),
    (77, "中景，机器人跑向消防梯，快速攀爬向下", ["robot", "indoor", "gun"]),
    (78, "下到地面后巷，发现后面也有丧尸接近", ["zombie", "robot", "street"]),
    (79, "机器人背靠墙壁，两边都是丧尸，被包围", ["robot", "zombie", "gun"]),
    (80, "特写LED面部：快速思考的数据流动画，寻找生路", ["robot_face", "robot", "zombie"]),
    (81, "看到旁边的下水道井盖，快速决定", ["robot", "indoor", "street"]),
    (82, "中景，机器人蹲下拉起井盖，丧尸已经逼近", ["robot", "robot_hand", "zombie"]),
    (83, "特写手部用力拉开井盖，铁盖摩擦地面", ["robot_hand", "robot", "zombie"]),
    (84, "机器人跳入下水道，在最后一刻拉上井盖", ["robot", "indoor", "zombie"]),
    (85, "主观视角黑暗下水道，机器人打开头灯，光束照向前方", ["robot", "robot_face", "indoor"]),

    # ===== 第五幕：逃离 (Escape) =====
    # 86-105: 下水道逃亡，最终返回地面
    (86, "中景，机器人在下水道中行走，水没过脚踝，灯光晃动", ["robot", "indoor", "gun"]),
    (87, "下水道墙壁上的涂鸦和裂缝，年代久远", ["indoor", "robot", "gun"]),
    (88, "特写LED面部显示导航数据，地图叠加在视野上", ["robot_face", "robot", "indoor"]),
    (89, "听到下水道前方也有丧尸声音，机器人关灯", ["robot", "indoor", "zombie"]),
    (90, "黑暗中仅有LED微弱蓝光，缓慢前进", ["robot_face", "robot", "indoor"]),
    (91, "拐角处遇见下水道丧尸，近距离遭遇", ["zombie_close", "zombie", "robot"]),
    (92, "近距搏斗，机器人用匕首解决丧尸，安静利落", ["robot", "zombie", "gun"]),
    (93, "特写匕首刺入丧尸喉咙，黑色血液流出", ["zombie_close", "robot", "robot_hand"]),
    (94, "中景，机器人继续前进，找到出口梯子", ["robot", "indoor", "gun"]),
    (95, "攀爬梯子向上，推开井盖，夕阳光线射入", ["robot", "indoor", "sunset"]),
    (96, "机器人爬出地面，黄昏光线洒在身上", ["robot", "street", "sunset"]),
    (97, "环顾四周，发现已经到了小镇边缘", ["robot", "street", "sunset"]),
    (98, "远景，夕阳下小镇轮廓，机器人站在废墟中", ["robot", "street", "sunset"]),
    (99, "中景，机器人掸去身上尘土，LED显示疲惫表情", ["robot_face", "robot", "gun"]),
    (100, "拿出水壶喝水，机械手指擦拭嘴角", ["robot_hand", "robot", "sunset"]),
    (101, "转身看向来时的方向，街道上丧尸群还在远处游荡", ["zombie", "street", "robot"]),
    (102, "决定返回车辆，沿建筑边缘小心移动", ["robot", "street", "gun"]),
    (103, "中景跟拍，机器人走回车辆停放位置", ["robot", "street", "sunset"]),
    (104, "检查车辆，引擎盖重新盖上，准备出发", ["robot", "robot_hand", "gun"]),
    (105, "特写手部转动钥匙点火，引擎启动，仪表盘亮起", ["robot_hand", "robot", "gun"]),

    # ===== 第六幕：离去 (Departure) =====
    # 106-120: 离开小镇
    (106, "中景车内，机器人系安全带，看一眼小镇后视镜", ["robot", "robot_face", "gun"]),
    (107, "挂挡，踩油门，车辆缓缓驶离，镜头跟拍", ["robot", "street", "sunset"]),
    (108, "远景车辆驶出小镇，沿来时的公路远去", ["robot", "street", "sunset"]),
    (109, "车尾视角，小镇越来越小，夕阳映照", ["robot", "street", "sunset"]),
    (110, "车内特写LED面部露出微笑表情，蓝色温暖光芒", ["robot_face", "robot", "gun"]),
    (111, "主观视角，前方公路延伸向远方的山脉，天空渐暗", ["robot", "street", "sunset"]),
    (112, "特写手部打开收音机，传出沙哑的1950年代音乐", ["robot_hand", "robot", "gun"]),
    (113, "中景，机器人随音乐轻轻点头，放松状态", ["robot", "robot_face", "gun"]),
    (114, "远景车辆在公路上行驶，镜头慢速拉升，视野渐宽", ["robot", "street", "sunset"]),
    (115, "无人机视角，车辆变成小点行驶在荒漠公路上", ["robot", "street", "sunset"]),
    (116, "夕阳橙色光芒充满画面，车辆剪影在地平线上", ["robot", "street", "sunset"]),
    (117, "极远景，车辆消失在光芒中，荒漠辽阔", ["robot", "street", "sunset"]),
    (118, "字幕叠加：\"TO BE CONTINUED\" 原子朋克风格字体", ["sunset", "robot", "street"]),
    (119, "黑屏淡出，剩下一行小字 \"NEW HAVEN 1962\"", ["sunset", "robot", "gun"]),
    (120, "全黑，片尾字幕滚动音效:风声渐远", ["sunset", "robot", "zombie"]),
]

csv_path = "zombie_storyboard_full.csv"
with open(csv_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["prompt", "image_prompts", "num_frames", "frame_rate"])
    for shot_id, prompt, asset_keys in SHOTS:
        assets = "|".join(BASE_ASSETS[k] for k in asset_keys)
        writer.writerow([f"分镜{shot_id:03d}: {prompt}", assets, 121, 24])

print(f"生成 {len(SHOTS)} 个分镜 → {csv_path}")
total_secs = len(SHOTS) * 121 / 24
print(f"预估总时长: {total_secs:.0f} 秒 ({total_secs/60:.1f} 分钟)")
