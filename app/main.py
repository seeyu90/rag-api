import os
import uuid
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from pydantic import BaseModel

# LangChain 與 Qdrant 相關
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document

app = FastAPI(
    title="RAG MVP API",
    description="具備自學習功能的 RAG API，連接遠端 Ollama",
    version="1.0.0"
)

# --- 環境變數讀取 (增加模型設定) ---
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://192.168.26.109:11434")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.1:8b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")

# 初始化模型與 Embedding (改為從變數讀取)
embeddings = OllamaEmbeddings(base_url=OLLAMA_URL, model=OLLAMA_EMBED_MODEL)
llm = Ollama(base_url=OLLAMA_URL, model=OLLAMA_CHAT_MODEL)

# 初始化 Qdrant 客戶端
client = QdrantClient(host=QDRANT_HOST, port=6333)

def get_vector_store(collection_name: str):
    return QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embeddings,
    )

# 定義 Collection
doc_store = get_vector_store("documents")
feedback_store = get_vector_store("self_learning")

# --- 資料模型 (Pydantic Models) ---
class QueryResponse(BaseModel):
    answer: str
    sources: List[str]


class FeedbackRequest(BaseModel):
    query: str
    answer: str
    score: int


# --- API 端點 ---

@app.get("/health")
async def health():
    """檢查連線狀態"""
    return {"status": "ok", "remote_ollama": OLLAMA_URL}


@app.post("/api/v1/upload", tags=["Ingestion"])
async def upload_file(file: UploadFile = File(...)):
    """1. 上傳檔案、切片並匯入 Qdrant"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="目前僅支援 PDF 檔案格式")

    temp_path = f"temp_{uuid.uuid4()}_{file.filename}"

    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        loader = PyPDFLoader(temp_path)
        pages = loader.load_and_split()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=100,
            separators=["\n\n", "\n", "。", "！", "？", " ", ""]
        )
        chunks = splitter.split_documents(pages)

        for chunk in chunks:
            chunk.metadata["filename"] = file.filename

        doc_store.add_documents(chunks)

        return {
            "status": "success",
            "message": f"成功處理 {len(chunks)} 個文本片段",
            "filename": file.filename
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上傳失敗: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/api/v1/ask", response_model=QueryResponse, tags=["RAG"])
async def ask_question(query: str = Query(..., example="這份文件的重點是什麼？")):
    """2. 提問：結合文件與高分回饋"""
    try:
        # 同時檢索文件庫與高分回饋庫
        doc_results = doc_store.similarity_search(query, k=3)
        gold_results = feedback_store.similarity_search(query, k=1)

        context = "\n".join([d.page_content for d in doc_results])
        past_examples = "\n".join([d.page_content for d in gold_results])

        # 增加防呆：如果沒抓到內容，給予提示
        if not context.strip():
            context = "（目前文件庫中無相關內容）"

        prompt = f"""你是一個專業助手。請根據以下參考資訊回答問題。
        如果過去有類似的高分回答，請優先參考。

        【參考文件】：
        {context}

        【歷史優質參考】：
        {past_examples}

        問題：{query}
        回答："""

        # 調用 Ollama
        response = llm.invoke(prompt)
        
        return {
            "answer": response,
            "sources": [d.metadata.get("filename", "unknown") for d in doc_results]
        }
    except Exception as e:
        # 將錯誤詳細拋出，方便在 API 回應中看到
        raise HTTPException(status_code=500, detail=f"LLM 處理失敗: {str(e)}")


@app.post("/api/v1/feedback", tags=["Self-Learning"])
async def submit_feedback(fb: FeedbackRequest):
    """3. 自學習：將高分回答存入金標庫"""
    if fb.score >= 4:
        content = f"問題: {fb.query}\n優質回答: {fb.answer}"
        doc = Document(page_content=content, metadata={"score": fb.score})
        feedback_store.add_documents([doc])
        return {"message": "感謝回饋！此對話已加入自學習庫。"}
    return {"message": "感謝回饋！"}
