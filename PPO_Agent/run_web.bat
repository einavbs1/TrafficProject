@echo off
REM Launch the FlowGrid PPO web app -- this is FlowGrid's PPO interface.
REM Keeps this console window open so you can see the server log and press
REM Ctrl+C to stop it; your browser opens automatically once ready.
cd /d "%~dp0"
python "%~dp0comparison_web.py"
pause
