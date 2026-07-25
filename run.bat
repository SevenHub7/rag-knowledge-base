@echo off
chcp 65001 >nul
title RAG 企业知识库问答系统
cd /d "%~dp0"

echo ==========================================
echo   RAG 企业知识库问答系统
echo ==========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python 已就绪

REM 安装依赖
echo [1/2] 检查并安装依赖...
pip install -r requirements.txt -q 2>&1
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)
echo [OK] 依赖已安装

REM 检查 API Key
if not exist ".env" (
    echo.
    echo [提示] 首次运行需要配置 API Key
    copy .env.example .env >nul
    echo 已创建 .env 文件，请在打开的记事本中填入你的 DeepSeek API Key
    echo 保存后关闭记事本，本脚本将继续启动
    echo.
    notepad .env
)

REM 启动
echo [2/2] 启动服务...
echo.
echo ------------------------------------------
echo   前端界面: http://localhost:8000/
echo   API 文档: http://localhost:8000/docs
echo   按 Ctrl+C 停止服务
echo ------------------------------------------
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

REM 如果异常退出，停住窗口
echo.
echo [服务已停止]
pause
