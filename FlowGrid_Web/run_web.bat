@echo off
REM Launch FlowGrid_Web -- ONE process only. Builds the dashboard once
REM (npm run build) and starts its own backend (server.py), which serves
REM both the built UI and its live data API on the same port (8001).
REM Your browser opens automatically once ready. Never touches
REM PPO_Agent's separate comparison_web dev tool.
REM Keeps this console window open so you can see the server log and
REM press Ctrl+C to stop it.
cd /d "%~dp0"

if not exist node_modules call npm install
call npm run build

echo Starting FlowGrid_Web (http://127.0.0.1:8001) -- opens automatically
echo once ready. Allow up to 30 seconds the first time before Run Agent
echo works (importing torch / SUMO / stable-baselines3).
cd backend
python server.py
pause
