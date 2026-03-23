@echo off
set "PYTHON_EXE=C:\Users\rodri\Downloads\dev\miniconda\python.exe"

if not exist "%PYTHON_EXE%" (
    echo Python nao encontrado em:
    echo %PYTHON_EXE%
    pause
    exit /b 1
)

"%PYTHON_EXE%" "%~dp0Threads.py"
pause
