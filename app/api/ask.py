from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import QueryResponse
from app.rag.pipeline import run_rag_pipeline

router = APIRouter()


@router.post("/ask", response_model=QueryResponse)
async def ask_question(query: str = Query(...)):
    try:
        # 調用封裝好的 Pipeline
        answer, sources = run_rag_pipeline(query)

        return {"answer": answer, "sources": sources}
    except Exception as e:
        # 這會幫助你在 smoke test 看到具體 Python 報錯
        raise HTTPException(status_code=500, detail=str(e))
