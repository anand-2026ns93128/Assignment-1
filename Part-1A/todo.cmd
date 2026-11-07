@echo off
rem Smart Todo CLI launcher (Windows). Puts src\ on PYTHONPATH; needs no setup (SC-002).
setlocal
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
python -m smart_todo %*
exit /b %ERRORLEVEL%
