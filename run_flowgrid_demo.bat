@echo off
REM Launch the full FlowGrid demo -- both independent products at once.
REM   1. PPO comparison app  (developer tool)        http://127.0.0.1:8000
REM   2. FlowGrid_Web        (operations dashboard)  http://127.0.0.1:8001
REM
REM Each opens in its own window and stays open so you can read the server
REM log and press Ctrl+C to stop it. This script does not reimplement either
REM launcher, it simply starts both of the existing ones, so the npm build
REM step for FlowGrid_Web is not duplicated here.
REM
REM Neither product depends on the other. To run just one, use
REM PPO_Agent\run_web.bat or FlowGrid_Web\run_web.bat directly.
cd /d "%~dp0"

echo.
echo  Starting the full FlowGrid demo, two windows.
echo.
echo    PPO comparison app ....... http://127.0.0.1:8000
echo    FlowGrid_Web dashboard ... http://127.0.0.1:8001
echo.
echo  Each browser tab opens automatically once its server is ready.
echo  FlowGrid_Web builds its dashboard first, so allow up to about 30
echo  seconds before its Run Agent button works.
echo.

start "FlowGrid PPO Comparison App" /D "%~dp0PPO_Agent" "%~dp0PPO_Agent\run_web.bat"
start "FlowGrid_Web Dashboard" /D "%~dp0FlowGrid_Web" "%~dp0FlowGrid_Web\run_web.bat"

echo  Both launched. This window can be closed.
echo.
pause
