@echo off
echo ========================================
echo 金融趋势分析前端 - 开发环境启动
echo ========================================
echo.

REM 检查 node_modules 是否存在
if not exist "node_modules" (
    echo [1/2] 首次运行，正在安装依赖...
    call npm install
    if errorlevel 1 (
        echo.
        echo 错误: 依赖安装失败！
        echo 请检查网络连接或尝试手动运行: npm install
        pause
        exit /b 1
    )
    echo.
    echo 依赖安装完成！
    echo.
) else (
    echo [1/2] 依赖已安装，跳过安装步骤
    echo.
)

echo [2/2] 正在启动开发服务器...
echo.
echo 提示: 
echo - 开发服务器将在 http://localhost:3000 启动
echo - 请确保后端服务已在 http://localhost:8000 运行
echo - 按 Ctrl+C 可停止服务器
echo.
echo ========================================
echo.

call npm run dev

pause
