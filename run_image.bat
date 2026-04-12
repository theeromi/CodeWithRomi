@echo off
cd /d "%~dp0"

if not exist venv\Scripts\python.exe (
  echo Python environment not found. Running install.bat...
  call install.bat
  if errorlevel 1 exit /b 1
)

venv\Scripts\python.exe -c "import torch, diffusers, transformers, accelerate, sentencepiece, bitsandbytes" >nul 2>&1
if errorlevel 1 (
  echo Image dependencies are missing. Installing now...
  venv\Scripts\python.exe -m pip install torch diffusers transformers accelerate sentencepiece bitsandbytes
  if errorlevel 1 (
    echo Failed to install image dependencies.
    echo Try running install.bat manually and then re-run this command.
    pause
    exit /b 1
  )
)

if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat
python run_image.py %*
