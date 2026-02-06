from app.infra.qdrant import doc_store, feedback_store

def retrieve_context(query: str, k_docs=3, k_feedback=1, score_threshold=0.5):
    """
    執行 Multi-Vector 檢索：搜尋摘要，回傳原始全文。
    """
    try:
        # 1. 檢索文件庫 (這裡會比對摘要的向量)
        docs_with_score = doc_store.similarity_search_with_score(query, k=k_docs)
        
        filtered_docs = []
        print(f"\n--- 檢索診斷開始 (目標 K={k_docs}) ---")
        
        for i, (doc, score) in enumerate(docs_with_score):
            # 取得原始全文與摘要預覽
            original_text = doc.metadata.get("original_content")
            preview = doc.page_content[:30].replace("\n", " ")
            
            # 列印診斷資訊
            status = "PASS" if score >= score_threshold else "DROP"
            print(f"[{status}] 第 {i+1} 名 | 分數: {score:.4f} | 摘要: {preview}...")

            # 分數過濾
            if score >= score_threshold:
                # --- 關鍵動作：如果有原始全文，則替換掉摘要內容 ---
                if original_text:
                    doc.page_content = original_text
                    # 在 metadata 標記這是還原後的內容，方便後續觀察
                    doc.metadata["retrieval_mode"] = "multi_vector_restored"
                
                filtered_docs.append(doc)

        # 2. 檢索自學習金標庫
        gold_with_score = feedback_store.similarity_search_with_score(
            query, k=k_feedback
        )
        filtered_gold = [
            doc for doc, score in gold_with_score 
            if score >= (score_threshold - 0.1)
        ]

        print(f"🔍 檢索結果: 原始 {len(docs_with_score)} 筆 -> 最終保留 {len(filtered_docs)} 筆")
        print("--- 檢索診斷結束 ---\n")

        return filtered_docs, filtered_gold

    except Exception as e:
        print(f"❌ 檢索失敗: {e}")
        return [], []