"""启动入口 —— 原来的 Hello World 演示已挪走,应用本体在 app/src/main.py。

跑法(在 back-yueyue/ 目录下):
    uv run python runApp.py        # 带热重载
接口文档: http://127.0.0.1:8000/docs
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.src.main:app", host="127.0.0.1", port=8000, reload=True)
