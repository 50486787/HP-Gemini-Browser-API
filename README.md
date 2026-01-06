# HP-Gemini-Browser-API
把gemini网页端桥接为api形式，便于接入其他平台进行操作。Bridge the gemini web end into an api form to facilitate integration with other platforms for operation.

由gemini编写。



---

# 🤖 Gemini 网页自动化 API 系统操作说明书

## 📖 简介

本系统通过 Python + Playwright 接管本地 Chrome 浏览器，将 Google Gemini 网页版封装为 HTTP API。支持文本对话、图片生成（自动下载）及文件上传分析。

---

## 🛠️ 第一步：环境安装 (首次运行)

请确保电脑已安装 Python 3.8+。在项目文件夹下打开终端（CMD 或 PowerShell），执行以下命令安装依赖：

```bash
# 1. 安装 Python 库
pip install playwright fastapi uvicorn requests pillow

# 2. 安装浏览器驱动
playwright install chromium

```

---

## ⚙️ 第二步：Chrome 浏览器配置 (关键！)

**这一步至关重要，必须严格执行，否则图片无法被脚本捕获。**

### 1. 创建调试专用快捷方式

1. 找到电脑上的 Chrome 图标，右键复制一份，重命名为 **"Chrome-Debug"**。
2. 右键点击该快捷方式 -> **属性**。
3. 在 **"目标 (Target)"** 一栏的末尾，**添加一个空格**，然后粘贴以下参数：
```text
--remote-debugging-port=9222 --user-data-dir="C:\sel_chrome_profile"

```


*(注：`C:\sel_chrome_profile` 是独立的配置文件夹，不会影响你日常使用的 Chrome)*

### 2. 手动设置默认下载目录

脚本会自动在代码所在目录创建 `downloaded_images` 文件夹。你需要将 Chrome 的下载路径指向这里。

1. **先运行一次代码**（或者手动在项目根目录下新建一个文件夹命名为 `downloaded_images`）。
2. 双击刚才创建的 **"Chrome-Debug"** 快捷方式打开浏览器。
3. 在地址栏输入 `chrome://settings/downloads` 并回车。
4. **修改位置**：点击“更改”，将下载位置选择为你的项目目录下的 **`downloaded_images`** 文件夹。
* 例如你的代码在 `D:\MyGeminiProject`，则路径应为 `D:\MyGeminiProject\downloaded_images`。


5. **关闭询问**：确保 **“下载前询问每个文件的保存位置”** 选项处于 **关闭 (关闭状态)**。
* *原因：如果不关闭，下载时会弹出弹窗等待用户点击，脚本会因超时而失败。*



---

## 🚀 第三步：启动服务流程

每次使用时，请按以下顺序操作：

### 1. 打开浏览器并登录

1. 双击 **"Chrome-Debug"** 快捷方式。
2. 访问 [https://gemini.google.com/](https://gemini.google.com/)。
3. 登录你的 Google 账号，确保能看到聊天输入框。
4. **不要关闭此窗口**，保持开启状态。

### 2. 启动 API 服务器

双击运行项目目录下的 **`start_server.bat`**，或者在终端运行：

```bash
python server.py

```

当看到 `Uvicorn running on http://127.0.0.1:8000` 时，服务启动成功。

---

## 📡 第四步：API 调用说明

### 接口信息

* **地址**: `http://127.0.0.1:8000/chat`
* **方式**: `POST`
* **格式**: `application/json`

### 请求参数示例

**1. 普通对话 / 生成图片**

```json
{
  "user_input": "生成一张赛博朋克风格的猫",
  "new_chat": true
}

```

**2. 上传图片并分析**

```json
{
  "user_input": "这张图里有什么？",
  "file_path": "D:\\images\\test_photo.jpg",
  "new_chat": true
}

```

### 使用测试脚本

你可以直接运行提供的 `test_api.py` 来验证功能：

1. 打开 `test_api.py`。
2. 修改 `target_file` 为你本地真实存在的图片路径（如果不需要上传可设为 `None`）。
3. 运行：
```bash
python test_api.py

```



---

## 📂 目录结构说明

系统运行后会维护以下文件夹：

| 文件夹名 | 用途 | 注意事项 |
| --- | --- | --- |
| **downloaded_images/** | **存放 Gemini 生成的图片** | **必须将 Chrome 默认下载路径设为此处！** |
| **json_output_cache/** | 存放每次 API 交互的完整 JSON 记录 | 包含文字回复和图片路径，方便回溯。 |
| **temp_upload_cache/** | 存放上传文件的临时副本 | 用于解决中文路径或文件占用问题，会自动清理。 |

---

## ❓ 常见问题排查

**Q: 为什么图片下载了，但程序提示“等待超时”或 JSON 里没有路径？**

* **A1 (路径不对):** 请检查 Chrome 的默认下载路径是否设置正确，是否指向了代码目录下的 `downloaded_images`。
* **A2 (弹窗阻挡):** 请检查 Chrome 设置里是否**关闭**了“下载前询问每个文件的保存位置”。
* **A3 (文件未完成):** 现在的代码会忽略 `.crdownload` 文件，必须等文件完全下完（网速慢时可能会超过 60秒 超时）。

**Q: 启动 `server.py` 报错 `Connection refused`？**

* **A:** 说明浏览器没有开启调试端口。请务必通过添加了 `--remote-debugging-port=9222` 参数的快捷方式启动 Chrome。

**Q: 能否同时并发多个请求？**

* **A:** **不能**。因为是控制同一个鼠标/键盘操作网页，必须排队处理。FastAPI 会自动将请求排队，按顺序执行。
