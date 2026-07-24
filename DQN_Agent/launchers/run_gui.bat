@echo off
REM Launch FlowGrid GUI in its own process so closing this window does NOT close the app.
cd /d "%~dp0"

where pythonw >nul 2>&1
if %ERRORLEVEL%==0 (
    start "FlowGrid" pythonw "%~dp0flowgrid_gui.py"
) else (
    start "FlowGrid" python "%~dp0flowgrid_gui.py"
)
exit /b 0
