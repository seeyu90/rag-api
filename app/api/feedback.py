from fastapi import APIRouter
from langchain.docstore.document import Document

from app.domain.feedback import FeedbackDomain  # 引入領域邏輯
from app.infra.qdrant import feedback_store
from app.models.schemas import FeedbackRequest

router = APIRouter()


@router.post("/feedback")
async def submit_feedback(fb: FeedbackRequest):
    # 使用 Domain 規則進行判斷
    if FeedbackDomain.is_worthy_for_learning(fb):
        content = FeedbackDomain.format_for_gold_standard(fb)
        doc = Document(
            page_content=content, metadata={"score": fb.score, "type": "gold_standard"}
        )
        feedback_store.add_documents([doc])
        return {"status": "learned", "message": "此案例已納入自學習庫"}

    return {"status": "received", "message": "感謝回饋"}
