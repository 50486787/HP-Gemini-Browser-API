import requests
import json
import os

# API 地址 (确保 server.py 已经运行)
url = "http://127.0.0.1:8000/chat"

# === 这里配置你要测试的文件 ===
# 替换为你电脑上真实存在的文件路径
target_file = r"G:\连接网页gemini\downloaded_images\Gemini_Generated_Image_r1xcl4r1xcl4r1xc.png"

# 客户端预检查：确保文件存在
if target_file and not os.path.exists(target_file):
    print(f"⚠️ 警告: 本地找不到文件 -> {target_file}")
    # 你可以选择在这里 exit()，或者继续测试(看看服务端怎么报错)

# 准备要发送的数据 (JSON)
payload = {
    "user_input": "把这张图片还原成真实效果图",

    # 关键修改：这里的键名必须是 "file_path"，与 server.py 里的定义一致
    "file_path": target_file,

    "new_chat": False
}

print(f">>> 正在发送请求给 API (文件: {os.path.basename(target_file)})...")

try:
    # 发送 POST 请求
    response = requests.post(url, json=payload)

    # 打印返回结果
    if response.status_code == 200:
        data = response.json()
        print("\n✅ API 调用成功！服务端返回结果：")
        print("-" * 40)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        print("-" * 40)
    else:
        print(f"\n❌ 调用失败 (状态码 {response.status_code}):")
        print(response.text)

except Exception as e:
    print(f"\n❌ 无法连接服务器 (请检查 server.py 是否运行): {e}")