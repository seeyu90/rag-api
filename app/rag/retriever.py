from app.infra.qdrant import doc_store, feedback_store
from app.infra.ollama import llm

def retrieve_context(query: str, k_docs=5, k_feedback=1, score_threshold=0.45):
    """
    執行跨語言 Multi-Vector 檢索：
    1. 中文問題轉英文關鍵字 (改善檢索分數)
    2. 搜尋英文摘要向量
    3. 回傳中文原始條文 (供 LLM 回答)
    """
    try:
        # 1. 跨語言翻譯：將中文問題轉為英文檢索詞
        # Llama 3.1 在英文語義空間的匹配能力通常優於中文
        translate_prompt = f"Translate the following Chinese search query into concise English keywords for vector search. Query: {query}"
        eng_query = llm.invoke(translate_prompt).strip()
        
        print(f"\n[跨語言檢索] 原始問題: {query}")
        print(f"[跨語言檢索] 轉譯關鍵字: {eng_query}")

        # 2. 檢索文件庫 (使用英文檢索詞)
        docs_with_score = doc_store.similarity_search_with_score(eng_query, k=k_docs)
        
        filtered_docs = []
        print(f"--- 檢索診斷開始 (目標 K={k_docs}) ---")
        
        for i, (doc, score) in enumerate(docs_with_score):
            original_text = doc.metadata.get("original_content")
            # 取得英文摘要預覽 (避開 Python 3.8 f-string 反斜線限制)
            eng_preview = doc.page_content[:40].replace("\n", " ")
            
            # 分數判定 (英文對英文的分數通常會比中文對中文穩定)
            status = "PASS" if score >= score_threshold else "DROP"
            print(f"[{status}] 第 {i+1} 名 | 分數: {score:.4f} | 英文摘要: {eng_preview}...")

            if score >= score_threshold:
                # 關鍵動作：將內容替換回中文原始條文
                if original_text:
                    doc.page_content = original_text
                    doc.metadata["retrieval_mode"] = "cross_lingual_restored"
                
                filtered_docs.append(doc)

        # 3. 檢索自學習金標庫 (金標庫通常較小，可直接用中文比對或同樣轉英文)
        gold_with_score = feedback_store.similarity_search_with_score(query, k=k_feedback)
        filtered_gold = [
            doc for doc, score in gold_with_score 
            if score >= (score_threshold - 0.1)
        ]

        print(f"🔍 檢索結果: 保留 {len(filtered_docs)} 筆高品質中文條文")
        print("--- 檢索診斷結束 ---\n")

        return filtered_docs, filtered_gold

    except Exception as e:
        print(f"❌ 檢索失敗: {e}")
        return [], []