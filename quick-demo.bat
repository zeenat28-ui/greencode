@echo off
REM GreenCode Quick Demo Setup - Windows

echo.
echo GreenCode Auditor - Quick Demo Setup
echo ========================================
echo.

REM Check Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker not found. Install from https://docker.com
    exit /b 1
)

echo Docker found
echo.

echo Starting services...
docker-compose -f docker-compose.demo.yml up -d

echo.
echo GreenCode is starting!
echo.
echo Open in browser:
echo   Frontend: http://localhost:5173
echo   Backend API: http://localhost:8000/docs
echo.
echo Quick Demo Steps:
echo   1. Click Demo Login button
echo   2. Paste sample code
echo   3. Click Run Scan
echo   4. Review results
echo   5. Click Generate Fix
echo.
echo View logs: docker-compose -f docker-compose.demo.yml logs -f
echo Stop demo: docker-compose -f docker-compose.demo.yml down
echo.
pause
