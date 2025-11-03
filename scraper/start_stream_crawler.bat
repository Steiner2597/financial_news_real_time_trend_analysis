@echo off
chcp 65001 >nul
echo ========================================
echo Reddit 实时流式爬虫（持续监听模式）
echo 延迟 ^< 1分钟，一直运行直到手动关闭
echo ========================================
echo.

REM 切换到 scraper 目录（脚本所在目录）
cd /d "%~dp0"
echo 工作目录: %CD%
echo.

REM 检查 Python
python --version
if errorlevel 1 (
    echo [错误] 未找到 Python，请确保 Python 已安装并添加到 PATH
    pause
    exit /b 1
)
echo.

echo ========================================
echo 🔴 持续监听模式
echo ========================================
echo • 程序将持续运行，实时捕获新帖子
echo • 按 Ctrl+C 停止监听
echo • 自动重连：连接断开时会自动恢复
echo ========================================
echo.

REM 🔥 直接运行，不再循环重启
python "%~dp0crawlers\reddit_stream_crawler.py"

echo.
echo ========================================
echo 监听已停止
echo ========================================
pause
