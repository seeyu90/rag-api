from fastapi import FastAPI

# 確保導入你的 API 路由
from app.api import ask, feedback, upload

app = FastAPI(
    title="RAG MVP API", description="具備自學習功能的 RAG 系統", version="1.0.0"
)

# 註冊各個模組的路由
app.include_router(upload.router, prefix="/api/v1", tags=["Ingestion"])
app.include_router(ask.router, prefix="/api/v1", tags=["RAG"])
app.include_router(feedback.router, prefix="/api/v1", tags=["Self-Learning"])


@app.get("/health")
async def health():
    """檢查 API 狀態"""
    return {"status": "ok"}
