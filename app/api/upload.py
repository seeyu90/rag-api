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

router = APIRouter()

def clean_pdf_text(text: str) -> str:
    """ 
    萬用前處理：適用於規範文件與操作手冊
    """
    # --- 1. 移除 PDF 格式雜訊 ---
    text = re.sub(r'\[Image \d+\]', '', text) # 移除 [Image 84]
    text = re.sub(r'--- PAGE \d+ ---', '', text) # 移除分頁標註
    text = re.sub(r'\(?圖\s?\d+\.\d+-\d+\)?', '', text) # 移除 (圖5.8-4)
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text) # 移除獨立頁碼
    
    # --- 2. 語義結構標準化 ---
    # 處理手冊路徑：統一將『 → 』或『 -> 』轉換為『 > 』
    text = text.replace('→', ' > ') 
    text = re.sub(r'\s*->\s*', ' > ', text) 
    
    # 處理手冊步驟：將 ● 轉為明確標籤
    text = text.replace(' ● ', '\n- 步驟：')
    text = text.replace('●', '\n- 步驟：') # 預防沒有空格的情況
    
    # --- 3. 文本優化 ---
    text = text.replace('\r', '')  # 移除換行雜訊
    text = re.sub(r'\n+', '\n', text) # 合併多餘換行

    return text.strip()

def process_pdf_ingestion(temp_path: str, filename: str):
    try:
        print(f"\n[任務開始] 處理檔案: {filename}")
        loader = PyPDFLoader(temp_path)
        pages = loader.load()
        
        # 1. 執行前處理
        full_text = ""
        for page in pages:
            full_text += clean_pdf_text(page.page_content) + "\n"

        # 2. 切片 (建議 800-1000 確保條文完整)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=900, 
            chunk_overlap=200,
            separators=["\n\n", "\n", "。", "；", " ", ""]
        )
        # 手動建立帶有 clean 內容的 Document 對象
        raw_chunks = splitter.create_documents([full_text])
        total_chunks = len(raw_chunks)
        
        final_docs_to_index = []

        # 3. 英文摘要與知識點提取
        for i, chunk in enumerate(raw_chunks, 1):
            # 強制要求 LLM 生成英文摘要以提升搜尋準確度
            eng_summary_prompt = f"""
            Translate and summarize the following Chinese company policy into 3-5 concise English key points for vector search.
            Requirement: Keep specific numbers (e.g., 5000 TWD, 1 year). If it's TOC or empty, return 'SKIP'.
            
            Text:
            {chunk.page_content}
            
            English Summary:
            """
            
            try:
                eng_summary = llm.invoke(eng_summary_prompt).strip()
                
                if "SKIP" in eng_summary.upper() and len(eng_summary) < 20:
                    continue
                
                # 建立索引文件
                doc = Document(
                    page_content=eng_summary, # 存入英文摘要用於檢索
                    metadata={
                        "original_content": chunk.page_content, # 存入中文全文用於回答
                        "source_file": filename,
                        "is_summary": True
                    }
                )
                final_docs_to_index.append(doc)
                print(f"[進度 {i}/{total_chunks}] 英文摘要成功: {eng_summary[:50]}...")
            except Exception as e:
                print(f"摘要失敗: {e}")

        if final_docs_to_index:
            doc_store.add_documents(final_docs_to_index)
            print(f"[成功] {filename} 已寫入向量庫")

    finally:
        if os.path.exists(temp_path): os.remove(temp_path)


# 關鍵：這裡必須定義 UPLOAD_DIR ---
UPLOAD_DIR = "temp"

# 確保資料夾存在，否則 os.path.join 雖然沒問題，但寫入檔案時會報錯
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@router.post("/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    # 將檔案路徑指向 temp/ 資料夾
    file_id = str(uuid.uuid4())
    temp_path = os.path.join(UPLOAD_DIR, f"temp_{file_id}_{file.filename}")
    
    # 寫入暫存檔
    content = await file.read()
    with open(temp_path, "wb") as f:
        f.write(content)
    
    # 交給背景任務處理 (任務結束後會執行 os.remove)
    background_tasks.add_task(process_pdf_ingestion, temp_path, file.filename)
    
    return {
        "status": "processing", 
        "filename": file.filename,
        "message": "檔案已存至暫存區，後台正在進行清洗與跨語言摘要..."
    }