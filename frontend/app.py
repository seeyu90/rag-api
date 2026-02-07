import streamlit as st
import requests
import uuid

# 設定頁面配置
st.set_page_config(page_title="AMASTek AI 智能助手", page_icon="🤖", layout="wide")

# API 後端位址 (請依據你的設定調整)
BASE_URL = "http://localhost:3080/api/v1"

st.title("🤖 AMASTek 企業知識庫系統")
st.markdown("---")

# --- 側邊欄：文件上傳與管理 ---
with st.sidebar:
    st.header("📂 知識庫管理")
    uploaded_file = st.file_uploader("上傳 PDF (規範或手冊)", type="pdf")
    
    if st.button("🚀 開始上傳並分析"):
        if uploaded_file:
            with st.spinner("正在進行前處理與跨語言索引..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                try:
                    response = requests.post(f"{BASE_URL}/upload", files=files)
                    if response.status_code == 200:
                        st.success(f"✅ {uploaded_file.name} 上傳成功！背景處理中...")
                    else:
                        st.error("❌ 上傳失敗")
                except Exception as e:
                    st.error(f"連線錯誤: {e}")
        else:
            st.warning("請先選擇檔案")

# --- 主畫面：對話區 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# 顯示歷史訊息
for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # 如果是助手回答，且不是最新一筆，可以選擇性隱藏回饋按鈕或保留

# 使用者輸入
if prompt := st.chat_input("請輸入關於員工規範或系統操作的問題..."):
    # 1. 顯示使用者訊息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. 獲取 AI 回答
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            try:
                # 呼叫你的問答 API
                res = requests.post(f"{BASE_URL}/ask", params={"query": prompt})
                data = res.json()
                answer = data.get("answer", "無法取得回答")
                sources = data.get("sources", [])
                
                st.markdown(answer)
                if sources:
                    with st.expander("🔍 查看參考來源"):
                        for s in sources:
                            st.caption(s)
                
                # --- 自學習回饋介面 ---
                st.markdown("---")
                st.caption("這則回答準確嗎？您的回饋將幫助系統自學習。")
                col1, col2, col3 = st.columns([1, 1, 4])
                
                with col1:
                    if st.button("👍 準確", key=f"good_{len(st.session_state.messages)}"):
                        # 發送正向回饋給你的 /feedback API
                        fb_payload = {"query": prompt, "answer": answer, "score": 5, "comment": "User verified"}
                        requests.post(f"{BASE_URL}/feedback", json=fb_payload)
                        st.toast("感謝回饋，已記錄！")
                
                with col2:
                    # 使用者點擊修正，展開輸入框
                    if st.button("📝 修正", key=f"fix_{len(st.session_state.messages)}"):
                        st.session_state[f"show_fix_{idx}"] = True
                
                # 處理修正輸入
                if st.session_state.get(f"show_fix_{idx}"):
                    correct_text = st.text_area("請輸入正確的答案或補充說明：", key=f"input_{idx}")
                    if st.button("提交正確答案", key=f"submit_{idx}"):
                        fb_payload = {
                            "query": prompt, 
                            "answer": correct_text, # 這裡傳入使用者修正後的正確內容
                            "score": 1, 
                            "comment": "User Correction"
                        }
                        # 呼叫你原本就寫好的 /feedback API
                        fb_res = requests.post(f"{BASE_URL}/feedback", json=fb_payload)
                        if fb_res.status_code == 200:
                            st.success("✨ 已納入自學習庫，系統已變更聰明了！")
                        st.session_state[f"show_fix_{idx}"] = False
                
                st.session_state.messages.append({"role": "assistant", "content": answer})

            except Exception as e:
                st.error(f"檢索服務異常: {e}")