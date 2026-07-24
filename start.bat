@echo off
echo ========================================
echo   RAG Question Answering System
echo ========================================
echo.
echo Starting the server...
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run the application
python app.py

pause
