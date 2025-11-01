@echo off
chcp 65001 >nul
REM 启动处理器（事件驱动模式）

echo ========================================
echo 数据处理器
echo ========================================
echo.

cd /d "%~dp0Analysis"
python processor_event_driven.py

pause
