from app.infra.ollama import llm
from app.rag.guard import input_guard, output_guard
from app.rag.prompt import RAG_PROMPT_TEMPLATE
from app.rag.retriever import retrieve_context


def run_rag_pipeline(query: str):
    # 1. Input Guard
    if not input_guard(query):
        return "無效的提問內容。", []

    # 2. Retrieve (檢索)
    docs, gold = retrieve_context(query)

    # 3. Augment (增強上下文)
    context_text = "\n".join([d.page_content for d in docs])
    past_text = "\n".join([d.page_content for d in gold])

    # 4. Decide (決定是否足夠回答) - 簡易邏輯
    if not context_text.strip() and not past_text.strip():
        return "目前資料庫中沒有相關資訊可以回答您的問題。", []

    # 5. Generate (生成)
    full_prompt = RAG_PROMPT_TEMPLATE.format(
        context=context_text, past_examples=past_text, query=query
    )

    raw_answer = llm.invoke(full_prompt)

    # 6. Output Guard
    final_answer = output_guard(raw_answer)

    # 整理來源
    sources = list(set([d.metadata.get("filename", "未知來源") for d in docs]))

    return final_answer, sources
