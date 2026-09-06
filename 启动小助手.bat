@echo off
title 自动早晚安小助手

REM 自动早晚安小助手 - 一键启动脚本（无控制台窗口）
REM 双击本文件即可启动软件

cd /d "%~dp0"

if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "src\main.py"
) else if exist "pythonw.exe" (
    start "" "pythonw.exe" "src\main.py"
) else (
    REM 兜底：用 python.exe（会有控制台窗口）
    start "" python "src\main.py"
)

exit
