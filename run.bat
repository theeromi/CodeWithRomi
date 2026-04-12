@echo off
cd /d "%~dp0"

if not exist venv\Scripts\python.exe (
	echo Python environment not found. Running install.bat...
	call install.bat
	if errorlevel 1 exit /b 1
)

venv\Scripts\python.exe -c "import faster_whisper, moviepy, PIL" >nul 2>&1
if errorlevel 1 (
	echo Required dependencies are missing. Running install.bat...
	call install.bat
	if errorlevel 1 exit /b 1
)

if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat
python run_pipeline.py %*
