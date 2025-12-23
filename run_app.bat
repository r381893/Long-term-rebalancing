@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 啟動蜘蛛網回測系統...
streamlit run app.py
pause
