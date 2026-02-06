#!/bin/bash
# smoke_test.sh

API_URL="http://127.0.0.1:3080/api/v1"

echo "1. 測試 Health Check..."
curl -s http://127.0.0.1:3080/health | grep -q "ok" && echo "✅ 正常" || echo "❌ 失敗"

echo -e "\n2. 測試 Feedback 接口 (高分)..."
FB_RES=$(curl -s -X POST "$API_URL/feedback" \
     -H "Content-Type: application/json" \
     -d '{"query":"如何請假？","answer":"請去系統申請","score":5}')
echo "$FB_RES" | jq -e . > /dev/null && echo "✅ JSON 格式正確: $FB_RES" || echo "❌ 失敗: $FB_RES"

echo -e "\n3. 測試 Ask 接口 (含 URL 編碼)..."
# 使用 python3 快速進行 URL 編碼避免中文亂碼
QUERY="關於進修補助的規定？"
ENCODED_QUERY=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$QUERY'))")

ASK_RES=$(curl -s -X POST "$API_URL/ask?query=$ENCODED_QUERY" -H "accept: application/json")

# 檢查是否為有效的 JSON
if echo "$ASK_RES" | jq -e . > /dev/null 2>&1; then
    echo "✅ 成功獲取回答："
    echo "$ASK_RES" | jq -r '.answer'
    echo "📚 來源: $(echo "$ASK_RES" | jq -r '.sources | join(", ")')"
else
    echo "❌ 請求失敗，原始回應內容如下："
    echo "$ASK_RES"
fi