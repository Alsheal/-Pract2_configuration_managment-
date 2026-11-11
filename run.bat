@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv" (
    python -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
set PYTHONPATH=%CD%\src
python -m dependency_visualizer.main --config config.yaml

endlocal