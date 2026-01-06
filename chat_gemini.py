from playwright.sync_api import sync_playwright
import time
import os
import json
import glob
import shutil
import uuid
import datetime

# 引入 PIL (仅用于日志，且增加了非图片过滤)
try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# === 配置 ===
# 1. 下载图片的目录
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloaded_images")
if not os.path.exists(DOWNLOAD_DIR): os.makedirs(DOWNLOAD_DIR)

# 2. 上传文件的临时缓存目录
TEMP_UPLOAD_DIR = os.path.join(os.getcwd(), "temp_upload_cache")
if not os.path.exists(TEMP_UPLOAD_DIR): os.makedirs(TEMP_UPLOAD_DIR)

# 3. JSON 结果的保存目录
JSON_OUTPUT_DIR = os.path.join(os.getcwd(), "json_output_cache")
if not os.path.exists(JSON_OUTPUT_DIR): os.makedirs(JSON_OUTPUT_DIR)


def create_safe_temp_file(original_path):
    """创建副本以避免中文路径或占用问题"""
    try:
        if not os.path.exists(original_path): return None
        # 获取原始扩展名
        _, ext = os.path.splitext(original_path)
        if not ext: ext = ".txt"  # 默认给个后缀

        random_name = f"upload_{uuid.uuid4().hex[:8]}{ext}"
        safe_path = os.path.join(TEMP_UPLOAD_DIR, random_name)
        shutil.copy2(original_path, safe_path)
        return safe_path
    except Exception as e:
        print(f"   ⚠️ 创建临时文件失败: {e}")
        return original_path


def get_clean_prompt(user_input, ratio="auto", file_path=None):
    """优化提示词，防止非图片文件触发 PIL 逻辑"""
    prompt_suffix = ""
    ratio_map = {"16:9": ", 16:9 aspect ratio", "1:1": ", 1:1 aspect ratio"}

    # 简单的图片扩展名检查
    is_image = False
    if file_path:
        lower_path = file_path.lower()
        if lower_path.endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp')):
            is_image = True

    if ratio.lower() == "auto":
        # 只有确实是图片才去读取尺寸
        if is_image and file_path and os.path.exists(file_path) and HAS_PIL:
            try:
                with Image.open(file_path) as img:
                    print(f"      📐 [Auto] 原图尺寸: {img.width}x{img.height}")
            except:
                pass
    else:
        prompt_suffix = ratio_map.get(ratio, "")

    return user_input + prompt_suffix


def save_json_result(data):
    """统一保存 JSON 到指定目录"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:6]
        filename = f"gemini_response_{timestamp}_{unique_id}.json"
        save_path = os.path.join(JSON_OUTPUT_DIR, filename)

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f">>> 💾 JSON 已保存至: {save_path}")
        return save_path
    except Exception as e:
        print(f"   ❌ 保存 JSON 失败: {e}")
        return None


def send_to_gemini(user_input, file_path=None, ratio="auto", new_chat=True):
    with sync_playwright() as p:
        safe_file_path = None
        try:
            final_prompt = get_clean_prompt(user_input, ratio, file_path)

            print(">>> 🔌 连接浏览器...")
            # ⚠️ 确保终端运行: chrome.exe --remote-debugging-port=9222
            try:
                browser = p.chromium.connect_over_cdp("http://localhost:9222")
            except Exception as e:
                return {"status": "error", "message": f"连接浏览器失败，请确认 Chrome 是否已带端口启动: {e}"}

            default_context = browser.contexts[0]

            page = None
            for p_page in default_context.pages:
                if "google.com" in p_page.url:
                    page = p_page
                    break
            if not page: return {"status": "error", "message": "未找到页面 (请先打开 Gemini)"}

            # === 锁定下载路径 (这对 CDP 模式至关重要) ===
            try:
                client = default_context.new_cdp_session(page)
                client.send("Browser.setDownloadBehavior", {
                    "behavior": "allow",
                    "downloadPath": DOWNLOAD_DIR,
                    "eventsEnabled": True
                })
                print(f"   ⚙️ 下载路径已锁定: {DOWNLOAD_DIR}")
            except Exception as e:
                print(f"   ⚠️ 设置下载路径失败 (可能影响自动下载): {e}")

            if new_chat:
                print(">>> 🔄 状态: 新建对话 (重置上下文)...")
                page.goto("https://gemini.google.com/app")
                page.wait_for_selector("div[role='textbox'], div[contenteditable='true']", state="visible")
            else:
                print(">>> 🔗 状态: 继续对话 (保留上下文)...")

            selector = "message-content"
            initial_count = page.locator(selector).count()

            # --- 上传逻辑 (通用文件) ---
            if file_path and os.path.exists(file_path):
                safe_file_path = create_safe_temp_file(file_path)
                upload_target = safe_file_path if safe_file_path else file_path

                print(f">>> 📂 准备上传文件: {os.path.basename(upload_target)}")
                page.keyboard.press("Escape")
                time.sleep(0.5)

                try:
                    # 寻找加号按钮
                    plus_btn = page.locator(
                        "button[aria-label*='上传'], button[aria-label*='添加'], button[aria-label*='Add'], button[aria-label*='Expand']").last

                    if plus_btn.is_visible():
                        plus_btn.click()
                        time.sleep(1)

                        with page.expect_file_chooser(timeout=5000) as fc_info:
                            menu_item = page.locator("text=上传文件").or_(page.locator("text=Upload file")).last
                            if menu_item.is_visible():
                                menu_item.click()
                            else:
                                page.locator("div[role='menuitem']").first.click()

                        file_chooser = fc_info.value
                        file_chooser.set_files(upload_target)
                        print("      ✅ 文件已填入，等待处理 (5s)...")
                        time.sleep(5)
                        page.keyboard.press("Escape")
                    else:
                        print("      ⚠️ 找不到加号按钮")
                except Exception as e:
                    print(f"   ⚠️ 上传流程异常: {e}")
                    pass

            # --- 发送指令 ---
            print(f">>> 📝 发送: {final_prompt}")
            input_box = page.get_by_role("textbox")
            input_box.click()
            time.sleep(0.5)
            input_box.fill(final_prompt)
            page.keyboard.press("Enter")

            print(">>> ⏳ 等待生成...")
            local_image_paths = []
            final_text = ""
            previous_text = ""
            stable_count = 0

            # --- 监控生成与下载 ---
            # 超时时间 300秒
            for i in range(300):
                responses = page.locator(selector)

                if responses.count() > initial_count:
                    last_response = responses.nth(-1)
                    current_text = last_response.inner_text()

                    # 检测文本稳定性
                    if current_text == previous_text and len(current_text) > 5:
                        stable_count += 1
                    else:
                        stable_count = 0
                        previous_text = current_text

                    images = last_response.locator("img")

                    # === 分支 A: 发现图片 (生成图任务) ===
                    # ⚠️ 修复逻辑：使用文件监控，但增强了稳定性和过滤
                    if images.count() > 0:
                        first_img = images.first
                        box = first_img.bounding_box()

                        # 确保不是 loading icon
                        if box and box['width'] > 100:
                            time.sleep(2)  # 等待渲染
                            count = images.count()
                            print(f">>> ✅ 发现 {count} 张图，准备下载...")

                            # 1. 获取当前文件夹状态（基准）
                            current_files_set = set(os.listdir(DOWNLOAD_DIR))

                            for idx in range(count):
                                try:
                                    target_img = images.nth(idx)
                                    target_img.hover()
                                    time.sleep(0.5)

                                    download_btns = last_response.locator(
                                        "button[aria-label*='下载'], button[aria-label*='Download'], a[download]")

                                    # 智能匹配按钮
                                    target_btn = None
                                    if idx < download_btns.count():
                                        target_btn = download_btns.nth(idx)

                                    if not target_btn or not target_btn.is_visible():
                                        # 备用方案：尝试找所有可见的下载按钮
                                        for b_idx in range(download_btns.count()):
                                            btn = download_btns.nth(b_idx)
                                            if btn.is_visible():
                                                target_btn = btn  # 这是一个近似匹配
                                                break

                                    if target_btn:
                                        print(f"      ⬇️ 点击下载第 {idx + 1} 张...")
                                        target_btn.click()

                                        # === 核心修复：更强的等待文件落地逻辑 ===
                                        found_new_file = False
                                        # 循环检测 60 秒 (之前是 20秒)
                                        for w in range(60):
                                            time.sleep(1)
                                            now_files_set = set(os.listdir(DOWNLOAD_DIR))

                                            # 计算新增文件
                                            new_files = now_files_set - current_files_set

                                            # 关键：过滤掉 .crdownload 和 .tmp 文件
                                            valid_new_files = []
                                            for f in new_files:
                                                if not f.endswith('.crdownload') and not f.endswith('.tmp'):
                                                    full_p = os.path.join(DOWNLOAD_DIR, f)
                                                    # 确保文件大小大于 0 (下载完成)
                                                    if os.path.exists(full_p) and os.path.getsize(full_p) > 0:
                                                        valid_new_files.append(f)

                                            if valid_new_files:
                                                for new_file in valid_new_files:
                                                    full_path = os.path.join(DOWNLOAD_DIR, new_file)
                                                    print(f"      ✨ 检测到文件落地: {new_file}")
                                                    local_image_paths.append(full_path)

                                                    # 更新基准集合，防止下一轮重复检测
                                                    current_files_set.add(new_file)

                                                found_new_file = True
                                                break  # 跳出等待循环，处理下一张图

                                        if not found_new_file:
                                            print(f"      ⚠️ 等待第 {idx + 1} 张图片下载超时 (60s)，可能未成功。")
                                    else:
                                        print(f"      ⚠️ 找不到第 {idx + 1} 张图的下载按钮")

                                except Exception as e:
                                    print(f"      ❌ 第 {idx + 1} 张处理出错: {e}")
                                    pass

                            # 所有图片循环结束后，保存结果
                            final_text = last_response.inner_text()
                            final_result = {"status": "success", "text": final_text, "images": local_image_paths}

                            # 清理临时上传文件
                            if safe_file_path and os.path.exists(safe_file_path):
                                try:
                                    os.remove(safe_file_path)
                                except:
                                    pass

                            # 保存并返回
                            save_json_result(final_result)
                            return final_result

                    # === 分支 B: 纯文本回复 (分析文件任务) ===
                    elif stable_count >= 3:
                        print("\n>>> 📝 文本生成完成")
                        final_text = current_text
                        final_result = {"status": "success", "text": final_text, "images": []}

                        if safe_file_path and os.path.exists(safe_file_path):
                            try:
                                os.remove(safe_file_path)
                            except:
                                pass

                        print("-" * 20)
                        print(f"预览: {final_text[:100]}...")
                        print("-" * 20)

                        save_json_result(final_result)
                        return final_result

                print(".", end="", flush=True)
                time.sleep(1)

            return {"status": "error", "message": "超时"}

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    # === 测试部分 ===
    # 确保 Chrome 已启动: chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\selenum\AutomationProfile"

    print(f"🚀 开始测试...")

    result = send_to_gemini(
        user_input="生成一张赛博朋克风格的猫",
        file_path=None,
        ratio="1:1",
        new_chat=True
    )

    print("\n运行结束。")