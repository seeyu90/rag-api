# RAG MVP API 管理腳本
# ------------------------
SHELL := /bin/bash

# ------------------------
# 工具定義
# ------------------------
PY := .venv/bin/python
PIP := .venv/bin/pip
UVICORN := .venv/bin/uvicorn
PYTEST := .venv/bin/pytest
FLAKE8 := .venv/bin/flake8
BLACK := .venv/bin/black
ISORT := .venv/bin/isort

# 預設參數
PORT ?= 3080
HOST ?= 0.0.0.0
Q ?= 請自我介紹

# 向量資料庫集合名稱
COLLECTION_DOCS := documents
COLLECTION_LEARN := self_learning
COLLECTION_DIMENSION := 768

# 讀取環境變數檔案
-include .env
export $(shell [ -f .env ] && sed 's/=.*//' .env)

# ------------------------
# 幫助選單
# ------------------------
help:
	@echo "RAG API 控制中心"
	@echo "------------------------"
	@echo "1. 環境設定:"
	@echo "   make venv         - 建立 Python 虛擬環境"
	@echo "   make install      - 安裝套件依賴"
	@echo "   make up           - 啟動 Docker 容器 (Qdrant)"
	@echo "   make down         - 停止 Docker 容器"
	@echo ""
	@echo "2. 代碼與系統檢查:"
	@echo "   make format       - 自動代碼格式化 (Black/Isort)"
	@echo "   make check        - 系統診斷 (代碼規範 / Ollama / Qdrant / Docker)"
	@echo ""
	@echo "3. 資料庫操作:"
	@echo "   make init-db      - 初始化 Qdrant 集合"
	@echo "   make reset-db     - 清空 Qdrant 所有集合"
	@echo ""
	@echo "4. 開發與運行:"
	@echo "   make run          - 啟動 FastAPI 本地開發伺服器"
	@echo "   make ingest FILE=path/to/file.pdf - 上傳 PDF 並向量化"
	@echo "   make test-ask Q='問題' - 測試 RAG 問答"
	@echo "   make test         - 執行 Pytest 單元測試"
	@echo "   make smoke        - 執行系統冒煙測試 (需先啟動 make run)"

# ------------------------
# 環境初始化
# ------------------------
venv:
	python3 -m venv .venv
	$(PIP) install -U pip

install: venv
	$(PIP) install -r requirements.txt

up:
	docker compose up -d

down:
	docker compose down

# ------------------------
# 代碼格式與檢查
# ------------------------
format:
	@echo "執行代碼格式化..."
	@$(ISORT) .
	@$(BLACK) .
	@echo "格式化完成"

check: format
	@echo "-----------------------------------------------"
	@echo "系統診斷開始"
	@echo "-----------------------------------------------"

	@echo "[1/4] 代碼規範檢查 (Flake8)"
	@if [ -f $(FLAKE8) ]; then \
		$(FLAKE8) . --max-line-length=88 --exclude=.venv,venv,__pycache__ && echo "PASS: 代碼格式符合規範" || (echo "FAIL: 代碼格式不符，請修正"; exit 1); \
	else \
		echo "SKIP: 未發現 flake8 套件"; \
	fi

	@echo -e "\n[2/4] 環境變數與 Ollama 連線"
	@OLLAMA_TARGET=$$(grep -E "^[^#]*OLLAMA_BASE_URL=" .env | head -1 | cut -d'=' -f2- | tr -d '"' | tr -d "'" | tr -d ' ' | tr -d '\r'); \
	if [ -z "$$OLLAMA_TARGET" ]; then echo "FAIL: 未在 .env 設定 OLLAMA_BASE_URL"; exit 1; fi; \
	echo "目標位址: $$OLLAMA_TARGET"; \
	if curl -sf --connect-timeout 2 "$$OLLAMA_TARGET/api/tags" > /dev/null; then \
		echo "PASS: 遠端 Ollama 連線正常"; \
		echo "可用模型清單:"; \
		curl -s "$$OLLAMA_TARGET/api/tags" | jq -r '.models[].name' 2>/dev/null || echo "  (提示: 安裝 jq 工具可優化顯示結果)"; \
	else \
		echo "FAIL: 無法連線至 Ollama，請檢查網路或服務狀態"; \
		exit 1; \
	fi

	@echo -e "\n[3/4] Qdrant 向量資料庫狀態"
	@Q_HOST=$$(grep -E "^[^#]*QDRANT_HOST=" .env | head -1 | cut -d'=' -f2- | tr -d '"' | tr -d "'" | tr -d ' ' || echo "127.0.0.1"); \
	if curl -sf --connect-timeout 2 "http://$$Q_HOST:6333/" > /dev/null; then \
		echo "PASS: Qdrant 服務運作中"; \
		echo "現有集合 (Collections):"; \
		curl -s "http://$$Q_HOST:6333/collections" | jq -r '.result.collections[].name' 2>/dev/null || echo "  目前無任何集合"; \
	else \
		echo "FAIL: 無法連線至 Qdrant (目標: $$Q_HOST:6333)"; \
		exit 1; \
	fi

	@echo -e "\n[4/4] 容器運行狀態 (Docker)"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "Names|qdrant|rag-api" || echo "未發現相關執行中容器"

	@echo "-----------------------------------------------"
	@echo "系統檢查完成"
	@echo "-----------------------------------------------"

# ------------------------
# 執行與測試
# ------------------------
run:
	$(UVICORN) app.main:app --reload --host $(HOST) --port $(PORT)

ingest:
	@if [ -z "$(FILE)" ]; then \
		echo "錯誤: 請提供檔案路徑。範例: make ingest FILE=data/employee_rules.pdf"; \
		exit 1; \
	fi
	@if [ ! -f "$(FILE)" ]; then \
		echo "錯誤: 找不到檔案 $(FILE)"; \
		exit 1; \
	fi
	@echo "正在上傳並處理檔案: $(FILE)..."
	@curl -X 'POST' \
		"http://127.0.0.1:$(PORT)/api/v1/upload" \
		-H 'accept: application/json' \
		-H 'Content-Type: multipart/form-data' \
		-F "file=@$(FILE);type=application/pdf"
	@echo -e "\n處理完成"

test-ask:
	@if ! command -v jq &> /dev/null; then \
		echo "ERROR: jq 未安裝，請先安裝 jq"; \
		exit 1; \
	fi
	@echo "執行問答測試..."
	@QUERY_ENCODED=$$(echo "$(Q)" | jq -sRr @uri); \
	curl -v -X 'POST' \
		"http://127.0.0.1:$(PORT)/api/v1/ask?query=$$QUERY_ENCODED" \
		-H 'accept: application/json'

test:
	@echo "執行 Pytest..."
	PYTHONPATH=. $(PYTEST) app/tests -v

smoke:
	@echo "執行系統冒煙測試..."
	bash smoke_test.sh

# ------------------------
# 前端介面 (Streamlit):
# ------------------------
.PHONY: run-frontend
run-frontend:
	@echo "正在啟動 Streamlit 前端介面..."
	@if [ ! -f "frontend/app.py" ]; then \
		echo "錯誤: 找不到 frontend/app.py。請確認檔案已放置於正確路徑。"; \
		exit 1; \
	fi
	@# 檢查是否安裝 streamlit，若無則提示安裝
	@.venv/bin/streamlit run frontend/app.py --server.port 8501 --server.address $(HOST)

# ------------------------
# Qdrant 初始化
# ------------------------
init-db:
	@echo "正在初始化 Qdrant 集合 (維度: $(COLLECTION_DIMENSION))..."
	@Q_HOST=$$(grep -E "^[^#]*QDRANT_HOST=" .env | head -1 | cut -d'=' -f2- | tr -d '"' | tr -d "'" | tr -d ' ' || echo "127.0.0.1"); \
	curl -X PUT http://$$Q_HOST:6333/collections/$(COLLECTION_DOCS) \
		-H "Content-Type: application/json" \
		-d '{"vectors": {"size": $(COLLECTION_DIMENSION), "distance": "Cosine"}}'; \
	echo "\n---"; \
	curl -X PUT http://$$Q_HOST:6333/collections/$(COLLECTION_LEARN) \
		-H "Content-Type: application/json" \
		-d '{"vectors": {"size": $(COLLECTION_DIMENSION), "distance": "Cosine"}}'; \
	echo "\n初始化完成"

reset-db:
	@echo "重置向量資料庫集合..."
	@Q_HOST=$$(grep -E "^[^#]*QDRANT_HOST=" .env | head -1 | cut -d'=' -f2- | tr -d '"' | tr -d "'" | tr -d ' ' || echo "127.0.0.1"); \
	curl -s -X DELETE http://$$Q_HOST:6333/collections/$(COLLECTION_DOCS) > /dev/null; \
	curl -s -X DELETE http://$$Q_HOST:6333/collections/$(COLLECTION_LEARN) > /dev/null; \
	echo "重置完成 (已刪除: $(COLLECTION_DOCS), $(COLLECTION_LEARN))"

rebuild-db: reset-db init-db
	@echo "Qdrant 資料庫已重建完成"