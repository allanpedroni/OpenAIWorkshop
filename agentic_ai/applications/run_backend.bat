@echo off
REM Set UV environment variables to avoid OneDrive sync issues

REM Set UV cache outside OneDrive
set UV_CACHE_DIR=%LOCALAPPDATA%\uv\cache

REM Set UV tool dir outside OneDrive  
set UV_TOOL_DIR=%LOCALAPPDATA%\uv\tools

REM Set virtual environment outside OneDrive (optional - uses .venv by default)
REM set UV_PROJECT_ENVIRONMENT=%LOCALAPPDATA%\uv\envs\openai-workshop

echo UV environment variables set:
echo   UV_CACHE_DIR=%UV_CACHE_DIR%
echo   UV_TOOL_DIR=%UV_TOOL_DIR%
echo.

REM Run the backend
echo Starting backend...
uv run backend.py

pause
