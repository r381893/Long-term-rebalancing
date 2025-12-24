#!/bin/bash

# 蜘蛛網回測系統 - macOS 啟動腳本
# 雙擊即可啟動前端首頁

cd "$(dirname "$0")"

echo "🕸️ 啟動蜘蛛網回測系統..."
echo "================================"

# 檢查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 錯誤: 找不到 Python3"
    echo "請先安裝 Python: https://www.python.org/downloads/"
    read -p "按 Enter 關閉..."
    exit 1
fi

# 安裝必要套件
echo "📦 檢查必要套件..."
pip3 install flask flask-cors pandas numpy openpyxl -q

# 啟動 API 伺服器
echo "🚀 啟動伺服器..."
echo ""
echo "✅ 首頁網址: http://localhost:5001"
echo ""
echo "按 Ctrl+C 可停止伺服器"
echo "================================"

# 延遲後自動開啟瀏覽器
(sleep 2 && open "http://localhost:5001") &

# 啟動 Flask
python3 api.py
