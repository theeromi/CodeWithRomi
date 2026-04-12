@echo off
REM One-time setup: create venv and install dependencies.
REM Run from the project root: install.bat
setlocal EnableExtensions

cd /d "%~dp0"

set "HAS_WINGET=0"
where winget >nul 2>&1 && set "HAS_WINGET=1"

if exist TERMS.md (
  echo ----------------------------------------
  type TERMS.md
  echo ----------------------------------------
  set /p accept="Do you accept these terms? (yes/no): "
  if /i not "%accept%"=="yes" if /i not "%accept%"=="y" (
    echo Installation cancelled.
    pause
    exit /b 1
  )
  echo.
)

where python >nul 2>&1
if errorlevel 1 (
  echo Python not found on PATH.
  where py >nul 2>&1
  if errorlevel 1 (
    if "%HAS_WINGET%"=="1" (
      echo Attempting to install Python 3.12 via winget...
      winget install --id Python.Python.3.12 -e --silent --accept-source-agreements --accept-package-agreements
    ) else (
      echo Winget not found; cannot auto-install Python.
    )
  )
)

where python >nul 2>&1
if errorlevel 1 (
  where py >nul 2>&1
  if errorlevel 1 (
    echo Python installation was not found.
    echo Install Python 3.10+ from https://python.org and re-run install.bat
    pause
    exit /b 1
  )
)

where ffmpeg >nul 2>&1
if errorlevel 1 (
  if "%HAS_WINGET%"=="1" (
    echo ffmpeg not found. Attempting install via winget...
    winget install --id Gyan.FFmpeg -e --silent --accept-source-agreements --accept-package-agreements
  ) else (
    echo Warning: ffmpeg not found and winget unavailable. Video export may fail until ffmpeg is installed.
  )
)

where ollama >nul 2>&1
if errorlevel 1 (
  if "%HAS_WINGET%"=="1" (
    echo Ollama not found. Attempting install via winget...
    winget install --id Ollama.Ollama -e --silent --accept-source-agreements --accept-package-agreements
  ) else (
    echo Warning: Ollama not found and winget unavailable. Clip analysis stage requires Ollama.
  )
)

echo Creating virtual environment...
where python >nul 2>&1
if errorlevel 1 (
  py -3 -m venv venv
) else (
  python -m venv venv
)
if errorlevel 1 (
  echo Failed to create virtual environment.
  pause
  exit /b 1
)

call venv\Scripts\activate.bat
if errorlevel 1 (
  echo Failed to activate virtual environment.
  pause
  exit /b 1
)

echo Installing dependencies...
pip install --upgrade pip
echo.
echo Installing core pipeline dependencies (required)...
pip install -r requirements.txt
if errorlevel 1 (
  echo requirements.txt install failed. Retrying with required-only set...
  pip install faster-whisper moviepy pillow
  if errorlevel 1 (
    echo Failed to install required pipeline dependencies.
    pause
    exit /b 1
  )
)

echo Installing optional image-generation dependencies...
pip install torch diffusers transformers accelerate sentencepiece bitsandbytes
if errorlevel 1 (
  echo Warning: optional image-generation packages failed to install.
  echo Full video pipeline should still work. Thumbnail/transition generation may be unavailable.
)

venv\Scripts\python.exe -c "import torch, diffusers, transformers, accelerate, bitsandbytes, sentencepiece" >nul 2>&1
if errorlevel 1 (
  echo Warning: image-generation dependencies are incomplete.
  echo Thumbnails/transitions may fail until torch + diffusers stack is installed.
)

venv\Scripts\python.exe -c "import faster_whisper, moviepy, PIL" >nul 2>&1
if errorlevel 1 (
  echo Required imports failed after installation.
  echo Re-run install.bat or delete venv and try again.
  pause
  exit /b 1
)

echo.
echo Done. To run:
echo   run_gui.bat     - GUI
echo   run.bat "C:\path\to\video.mp4" --clips 5
echo.
echo If needed, pull models with:
echo   ollama pull qwen2.5:32b
echo   ollama pull qwen2.5:14b
echo   ollama pull llama3.1:8b
pause
