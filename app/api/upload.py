import os
import uuid
import time
import re
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema import Document
from app.infra.qdrant import doc_store
from app.infra.ollama import llm 
from app.rag.prompt import SUMMARY_PROMPT

router = APIRouter()

def clean_pdf_text(text: str) -> str:
    # 1. 移除圖片佔位符 [Image XX]
    text = re.sub(r'\[Image \d+\]', '', text)
    # 2. 移除分頁標籤 --- PAGE XX ---
    text = re.sub(r'--- PAGE \d+ ---', '', text)
    # 3. 移除孤立的頁碼 (假設頁碼通常是單獨一行)
    text = re.sub(r'\n \d+ \n', '\n', text)
    # 4. 將多個換行合併，但保留段落感
    text = re.sub(r'\n+', '\n', text)
    return text.strip()

# 將處理邏輯抽離成一個獨立的函數
def process_pdf_ingestion(temp_path: str, filename: str):
    """
    在背景執行的耗時任務
    """
    try:
        start_time = time.time()
        print(f"\n[背景任務] 開始處理檔案: {filename}")
        
        # 1. 載入與切片
        loader = PyPDFLoader(temp_path)
        pages = loader.load()
        for page in pages:
            page.page_content = clean_pdf_text(page.page_content)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=700, 
            chunk_overlap=100,
            separators=["\n\n", "\n", "。", "；", " ", ""]
        )
        raw_chunks = splitter.split_documents(pages)
        total_chunks = len(raw_chunks)
        
        final_docs_to_index = []
        
        # 2. 逐片產生摘要 (這是最耗時的地方)
        for i, chunk in enumerate(raw_chunks, 1):
            # --- 新增：顯示原始切片內容 ---
            print(f"\n>>> [片段 {i}/{total_chunks}] 原始內容展示:")
            # 取代換行符號方便閱讀，並只顯示前 200 字
            display_raw = chunk.page_content.replace('\n', ' ')
            print(f"    {display_raw[:200]}...")
            
            formatted_prompt = SUMMARY_PROMPT.format(text=chunk.page_content)
            try:
                summary_text = llm.invoke(formatted_prompt).strip()
                
                # 跳過 SKIP 內容
                if "SKIP" in summary_text.upper() and len(summary_text) < 15:
                    continue
                
                summary_doc = Document(
                    page_content=summary_text,
                    metadata={
                        "doc_id": str(uuid.uuid4()),
                        "source_file": filename,
                        "original_content": chunk.page_content,
                        "is_summary": True,
                        "page": chunk.metadata.get("page", 0)
                    }
                )
                final_docs_to_index.append(summary_doc)
                
                # 即使是背景執行，我們依然在終端機印出進度方便觀察
                clean_preview = summary_text[:30].replace("\n", " ")
                print(f"[背景進度 {i}/{total_chunks}] 摘要成功 | {clean_preview}...")
                
            except Exception as e:
                print(f"[背景進度 {i}/{total_chunks}] 失敗: {e}")
                final_docs_to_index.append(chunk)

        # 3. 寫入資料庫
        if final_docs_to_index:
            doc_store.add_documents(final_docs_to_index)
            print(f"[背景任務] 成功寫入 {len(final_docs_to_index)} 筆資料至 Qdrant")

        print(f"[背景任務] 檔案 {filename} 處理完成，總耗時: {time.time() - start_time:.2f}秒")

    except Exception as e:
        print(f"[背景任務] 嚴重錯誤: {str(e)}")
    finally:
        # 務必清理臨時檔案
        if os.path.exists(temp_path):
            os.remove(temp_path)

@router.post("/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    立刻回覆客戶端，並將任務丟到背景執行
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="僅支援 PDF")

    # 必須先將上傳的內容存下來，因為函數結束後 file stream 會關閉
    temp_path = f"temp_{uuid.uuid4()}_{file.filename}"
    content = await file.read()
    with open(temp_path, "wb") as f:
        f.write(content)

    # 將任務加入 FastAPI 的背景排程
    background_tasks.add_task(process_pdf_ingestion, temp_path, file.filename)

    return {
        "status": "received",
        "message": f"檔案 {file.filename} 已收到，系統正在後台進行摘要與向量化處理，請稍後再進行提問。",
        "task_id": str(uuid.uuid4())
    }