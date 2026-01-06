import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os

# 导入核心函数 (确保 chat_gemini.py 在同一目录下)
from chat_gemini import send_to_gemini

# 创建 API 实例
app = FastAPI(title="Gemini 自动化接口")


# === 定义请求的数据格式 ===
class GeminiRequest(BaseModel):
    user_input: str  # 必填：提示词
    file_path: Optional[str] = None  # 选填：文件路径 (注意：这里改名为 file_path 以匹配核心函数)
    ratio: str = "auto"  # 选填：比例
    new_chat: bool = True  # 选填：是否新建对话


@app.get("/")
def read_root():
    return {"message": "Gemini API 服务已运行! 请发送 POST 请求到 /chat"}


@app.post("/chat")
def chat_endpoint(request: GeminiRequest):
    """
    接收 JSON 请求 -> 调用 Playwright 脚本 -> 返回 JSON 结果
    """
    print(f"📥 收到请求: {request.user_input[:20]}... | 文件: {request.file_path}")

    # 1. 如果传了文件路径，先检查文件是否存在
    if request.file_path and not os.path.exists(request.file_path):
        print(f"❌ 错误: 文件路径不存在 -> {request.file_path}")
        return {
            "status": "error",
            "message": f"服务器上找不到该路径: {request.file_path}"
        }

    try:
        # 2. 调用 chat_gemini.py 里的核心函数
        # FastAPI 会自动把这个同步函数放在线程池里跑，不会卡死主线程
        result = send_to_gemini(
            user_input=request.user_input,
            file_path=request.file_path,  # 传入文件路径
            ratio=request.ratio,
            new_chat=request.new_chat
        )

        # 3. 直接返回结果 (FastAPI 会自动转为 JSON)
        # 结果格式形如: {"status": "success", "text": "...", "images": [...]}
        return result

    except Exception as e:
        print(f"❌ 服务端异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # 启动服务器
    # 访问 http://127.0.0.1:8000/docs 可以看到自动生成的测试界面
    print("🚀 API 服务启动中...")
    uvicorn.run(app, host="127.0.0.1", port=8000)