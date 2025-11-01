@echo off
chcp 65001 >nul
REM 自动清理 Redis 旧数据（保留 24 小时）

echo ========================================
echo Redis 数据清理工具
echo ========================================
echo.
echo 清理超过 24 小时的旧数据...
echo.

python clean_old_data.py

echo.
echo 清理完成
pause
