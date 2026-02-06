def input_guard(query: str) -> bool:
    """檢查輸入是否包含敏感詞或無意義字元"""
    if len(query.strip()) < 2:
        return False
    # 可以在此加入敏感詞過濾邏輯
    return True


def output_guard(answer: str) -> str:
    """規範化回答內容"""
    if not answer or len(answer.strip()) < 5:
        return "抱歉，我無法從文件中整理出有效的回答。"
    return answer.strip()
