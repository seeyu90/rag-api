# RAG API MVP：自學習向量檢索系統

這是一個基於 FastAPI 與 LangChain 構建的 RAG（Retrieval-Augmented Generation）系統。支援檔案向量化、自動問答，並具備基於使用者回饋的「自學習」強化機制。

---

## 🛠 功能特色

* **多檔案處理**：支援 PDF 上傳並自動進行文本切片與向量化存儲。
* **遠端 LLM 整合**：透過環境變數彈性配置遠端 Ollama 服務與模型名稱。
* **高效向量檢索**：使用 Qdrant 作為向量資料庫，支援高維度 Cosine 相似度計算。
* **自學習循環**：透過 `/feedback` 接口收集評分，高分問答將進入「金標庫」以優化後續檢索。
* **自動化管理**：完整 Makefile 整合，涵蓋診斷、初始化、格式化與測試。

---

## 🏗 技術棧

* **Framework**：FastAPI（Python 3.8+）
* **LLM / Embedding**：Ollama（可於 `.env` 自定義模型，如 `llama3.1`、`nomic-embed-text`）
* **Vector Database**：Qdrant（預設 Port 6333）
* **Orchestration**：LangChain、langchain-qdrant
* **DevOps**：Docker、Docker Compose、Makefile

---

## 🚦 快速開始

### 1️⃣ 環境設定

複製並修改環境變數，確保 `OLLAMA_BASE_URL` 指向正確的伺服器：

```bash
cp .env.example .env
# 編輯 .env 設定模型名稱與 URL
# OLLAMA_CHAT_MODEL=llama3.1:8b
# OLLAMA_EMBED_MODEL=nomic-embed-text:latest
```

---

### 2️⃣ 基礎設施啟動（Docker）

使用 Docker Compose 啟動 Qdrant 向量資料庫：

```bash
make up
```

---

### 3️⃣ 初始化資料庫

在第一次執行前，必須先建立 Qdrant 集合（預設維度 768）：

```bash
make init-db
```

---

### 4️⃣ 啟動 API 伺服器

```bash
make run
```

服務啟動後，請訪問：

* [http://localhost:8000/docs](http://localhost:8000/docs)

查看自動生成的 Swagger 文件。

---

### 5️⃣ Docker 啟動（完整服務）

使用 Compose 快速建構並啟動服務：

```bash
make up
```

服務啟動後，請訪問：

* [http://localhost:8000/docs](http://localhost:8000/docs)

查看自動生成的 API 文件。

---

## 🧪 開發與操作指令（Makefile）

| 指令 | 功能說明 |
| --- | --- |
| `make check` | 全系統診斷：檢查代碼格式、Ollama 連線、Qdrant 狀態與模型列表 |
| `make format` | 自動格式化代碼（Black & Isort） |
| `make ingest FILE=path/to.pdf` | 上傳 PDF 文件並進行向量化處理 |
| `make test-ask Q="問題內容"` | 快速測試 RAG 問答功能 |
| `make reset-db` | 清空所有向量資料集（慎用） |

---

## 📡 API 端點簡介

| 方法 | 路徑 | 功能 |
| ---- | ------------------ | ---------------------- |
| POST | `/api/v1/upload`   | 上傳檔案並匯入向量資料庫 |
| POST | `/api/v1/ask`      | 提問並獲得基於 RAG 的回答 |
| POST | `/api/v1/feedback` | 送出回饋評分（用於自學習機制）|
| GET  | `/health`          | 檢查 API 與遠端 Ollama 連線狀態 |

---

## 🧠 自學習機制說明

當使用者對回答給予 **4 分以上（滿分 5）** 的評價時，系統會將該次 **(Question, Answer)** 對存入 `self_learning` 集合。

在下一次提問時，系統將執行以下流程：

1. 同時檢索：

   * **原始文件庫**
   * **歷史高分回饋庫**
2. 將歷史優質回答作為 **Few-shot Prompt** 提供給模型參考。
3. 達成動態優化輸出品質的效果。

---

## 📂 專案結構

```plaintext
.
├── app/
│   ├── main.py          # 主程式與 API 邏輯
│   └── tests/           # Pytest 測試案例
├── qdrant_data/         # 向量資料庫持久化目錄（已加入 .gitignore）
├── .env                 # 環境變數配置（模型名稱、URL）
├── Dockerfile
├── docker-compose.yml
└── Makefile             # 自動化維運腳本
```

---

> **注意事項**
> `qdrant_data/` 目錄包含資料庫狀態，請勿提交至 Git 倉庫。
