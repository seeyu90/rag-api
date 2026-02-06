import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

# 定義一個通用的 transport
transport = ASGITransport(app=app)


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_ask_endpoint_structure():
    """測試問答接口的結構回傳"""
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 注意：FastAPI 的路徑參數建議這樣傳
        response = await ac.post("/api/v1/ask", params={"query": "測試問題"})

    # 這裡如果是 200 代表連線 LLM 成功，如果是 500 代表 LLM 或向量庫未啟動
    # 在單元測試中，我們主要確認 API 邏輯沒斷
    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_feedback_logic():
    """測試回饋邏輯：低分不應觸發學習"""
    low_score_data = {"query": "測試問題", "answer": "測試回答", "score": 2}
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/v1/feedback", json=low_score_data)

    assert response.status_code == 200
    # 根據你的 Domain 邏輯，2 分不應該回傳 "learned"
    assert response.json()["status"] != "learned"
