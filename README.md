# RAG API MVP: 自學習向量檢索系統

這是一個基於 FastAPI 與 LangChain 構建的 RAG (Retrieval-Augmented Generation) 系統。支援檔案向量化、自動問答，並具備基於使用者回饋的「自學習」強化機制。

## 🛠 功能特色
* 多檔案處理: 支援 PDF 上傳並自動進行文本切片與向量化存儲。
* 遠端 LLM 整合: 預設連接至遠端 Ollama 服務。
* 自學習循環: 透過 /feedback 接口收集評分，高分問答將進入「金標庫」優化後續檢索。
* 容器化開發: 完整 Docker 支持，一鍵啟動開發/測試環境。
* 品質保證: 內建 Flake8 代碼檢查與 Pytest 單元測試。

## 🏗 技術棧
* Framework: FastAPI (Python 3.11+)
* LLM/Embedding: Ollama (Models: llama3, nomic-embed-text)
* Vector Database: ChromaDB
* Orchestration: LangChain
* DevOps: Docker, Docker-compose

## 🚦 快速開始
1. 預置條件確保遠端伺服器的 Ollama 已啟動，並允許外部連線：
```Bash
# 在遠端機器上設定環境變數
export OLLAMA_HOST=0.0.0.0
ollama serve
```
2. 環境設定複製環境變數範例：
```Bash
cp .env.example .env
# 請確認 .env 中的 OLLAMA_BASE_URL=http://192.168.26.109:11434
```
3. Docker 啟動
使用 Compose 快速建構並啟動服務：
```Bash
docker-compose up --build
```
服務啟動後，訪問 http://localhost:8000/docs 查看自動生成的 API 文件。

## 🧪  開發與測試
代碼風格檢查 (Flake8)我們遵循 PEP 8 規範，執行以下指令進行檢查：
```Bash
docker-compose run --rm rag-api flake8 .
```
運行單元測試 (Pytest)
```Bash
docker-compose run --rm rag-api pytest app/tests
```
## 📡 API 端點簡介
方法路徑功能
POST/api/v1/upload上傳檔案並匯入向量資料庫
POST/api/v1/ask提問並獲得基於 RAG 的回答
POST/api/v1/feedback送出回饋評分 (用於自學習機制)
GET/health檢查 API 與遠端 Ollama 連線狀態

## 🧠 自學習機制說明
當使用者對回答給予 4 分以上 (滿分 5) 的評價時，系統會將該次 (Question, Answer) 對存入 `feedback_collection`。在下一次提問時，系統會：
1. 同時檢索「原始文件」與「高分歷史對話」。
2. 將歷史優質回答作為 Few-shot Prompt 提供給模型參考。
3. 達成動態優化輸出質量的效果。

## 📂 專案結構Plaintext.
├── app/
│   ├── api/            # API Router 與 Endpoint
│   ├── core/           # RAG 核心邏輯 (Embedding, Retrieval)
│   ├── models/         # Pydantic 資料結構
│   └── tests/          # Pytest 測試案例
├── chroma_db/          # 向量資料庫持久化目錄
├── .flake8             # Style check 配置
├── docker-compose.yml
└── Dockerfile