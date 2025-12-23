@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo   蜘蛛網回測系統 - 前端 Dashboard
echo ========================================
echo.
echo 正在啟動 Flask API 伺服器...
echo 前端網址: http://localhost:5000
echo.
echo 按 Ctrl+C 可停止伺服器
echo ----------------------------------------
python api.py
pause
