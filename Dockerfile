FROM python:3.8-slim

WORKDIR /app

# 安裝系統依賴（若有需要）
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# 複製依賴清單並安裝
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製程式碼
COPY . .

# 啟動指令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]