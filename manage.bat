@echo off
REM GEE System Management Script for Windows
REM Manages both Forge (Python) and Praxis (Go) processes

setlocal enabledelayedexpansion

REM Configuration
set FORGE_DIR=Forge
set PRAXIS_DIR=Praxis
set FORGE_PORT=5000
set PRAXIS_PORT=8080
set PID_DIR=%TEMP%\gee

REM Create PID directory if it doesn't exist
if not exist "%PID_DIR%" mkdir "%PID_DIR%"

REM Parse command
if "%1"=="" goto usage
if "%1"=="start" goto start_all
if "%1"=="stop" goto stop_all
if "%1"=="restart" goto restart_all
if "%1"=="status" goto status
if "%1"=="logs" goto logs
if "%1"=="forge-start" goto start_forge
if "%1"=="forge-stop" goto stop_forge
if "%1"=="forge-restart" goto restart_forge
if "%1"=="praxis-start" goto start_praxis
if "%1"=="praxis-stop" goto stop_praxis
if "%1"=="praxis-restart" goto restart_praxis
goto usage

:start_all
echo [GEE] Starting GEE System...
if not exist logs mkdir logs
call :start_forge_proc
call :start_praxis_proc
call :show_status
goto end

:stop_all
echo [GEE] Stopping GEE System...
call :stop_forge_proc
call :stop_praxis_proc
call :show_status
goto end

:restart_all
echo [GEE] Restarting GEE System...
call :stop_forge_proc
call :stop_praxis_proc
timeout /t 2 /nobreak > nul
call :start_forge_proc
call :start_praxis_proc
call :show_status
goto end

:status
call :show_status
goto end

:logs
echo [GEE] Opening log files...
if exist logs\forge.log start notepad logs\forge.log
if exist logs\praxis.log start notepad logs\praxis.log
goto end

:start_forge
call :start_forge_proc
goto end

:stop_forge
call :stop_forge_proc
goto end

:restart_forge
call :stop_forge_proc
timeout /t 1 /nobreak > nul
call :start_forge_proc
goto end

:start_praxis
call :start_praxis_proc
goto end

:stop_praxis
call :stop_praxis_proc
goto end

:restart_praxis
call :stop_praxis_proc
timeout /t 1 /nobreak > nul
call :start_praxis_proc
goto end

REM Function to start Forge
:start_forge_proc
echo [GEE] Starting Forge (Python Rules Engine)...

REM Check if already running
if exist "%PID_DIR%\forge.pid" (
    set /p FORGE_PID=<"%PID_DIR%\forge.pid"
    tasklist /FI "PID eq !FORGE_PID!" 2>nul | find "!FORGE_PID!" >nul
    if !errorlevel!==0 (
        echo [WARNING] Forge is already running
        exit /b 1
    )
)

cd %FORGE_DIR%

REM Apply database updates if needed
if exist db_updates_praxis.sql if exist instance\GEE.db (
    echo [GEE] Applying database updates...
    sqlite3 instance\GEE.db < db_updates_praxis.sql 2>nul
)

REM Start Forge
echo [GEE] Starting Forge on port %FORGE_PORT%...
start /b cmd /c "python app.py > ..\logs\forge.log 2>&1"

REM Get the PID (this is approximate in Windows)
timeout /t 2 /nobreak > nul
for /f "tokens=2" %%i in ('tasklist /v ^| findstr /i "python.exe" ^| findstr /i "app.py"') do (
    echo %%i > "%PID_DIR%\forge.pid"
    echo [GEE] Forge started successfully on port %FORGE_PORT%
    goto forge_started
)
echo [ERROR] Failed to start Forge
:forge_started

cd ..
exit /b 0

REM Function to start Praxis
:start_praxis_proc
echo [GEE] Starting Praxis (Go Rules Execution Engine)...

REM Check if already running
if exist "%PID_DIR%\praxis.pid" (
    set /p PRAXIS_PID=<"%PID_DIR%\praxis.pid"
    tasklist /FI "PID eq !PRAXIS_PID!" 2>nul | find "!PRAXIS_PID!" >nul
    if !errorlevel!==0 (
        echo [WARNING] Praxis is already running
        exit /b 1
    )
)

cd %PRAXIS_DIR%

REM Create data directory if it doesn't exist
if not exist data mkdir data

REM Check if Go is installed
where go >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Go is not installed or not in PATH
    echo [ERROR] Please install Go 1.21+ from https://golang.org/dl/
    cd ..
    exit /b 1
)

REM Build Praxis if not already built
if not exist praxis.exe (
    echo [GEE] Building Praxis...
    go build -o praxis.exe cmd/praxis/main.go
)

REM Start Praxis
echo [GEE] Starting Praxis on port %PRAXIS_PORT%...
start /b cmd /c "praxis.exe > ..\logs\praxis.log 2>&1"

REM Get the PID (this is approximate in Windows)
timeout /t 2 /nobreak > nul
for /f "tokens=2" %%i in ('tasklist /v ^| findstr /i "praxis.exe"') do (
    echo %%i > "%PID_DIR%\praxis.pid"
    echo [GEE] Praxis started successfully on port %PRAXIS_PORT%
    goto praxis_started
)
echo [ERROR] Failed to start Praxis
:praxis_started

cd ..
exit /b 0

REM Function to stop Forge
:stop_forge_proc
echo [GEE] Stopping Forge...

if exist "%PID_DIR%\forge.pid" (
    set /p FORGE_PID=<"%PID_DIR%\forge.pid"
    taskkill /PID !FORGE_PID! /F >nul 2>&1
    del "%PID_DIR%\forge.pid"
    echo [GEE] Forge stopped
) else (
    echo [WARNING] Forge is not running
)
exit /b 0

REM Function to stop Praxis
:stop_praxis_proc
echo [GEE] Stopping Praxis...

if exist "%PID_DIR%\praxis.pid" (
    set /p PRAXIS_PID=<"%PID_DIR%\praxis.pid"
    taskkill /PID !PRAXIS_PID! /F >nul 2>&1
    del "%PID_DIR%\praxis.pid"
    echo [GEE] Praxis stopped
) else (
    echo [WARNING] Praxis is not running
)
exit /b 0

REM Function to show status
:show_status
echo.
echo === GEE System Status ===
echo.

if exist "%PID_DIR%\forge.pid" (
    set /p FORGE_PID=<"%PID_DIR%\forge.pid"
    tasklist /FI "PID eq !FORGE_PID!" 2>nul | find "!FORGE_PID!" >nul
    if !errorlevel!==0 (
        echo Forge:  Running (PID: !FORGE_PID!) on port %FORGE_PORT%
    ) else (
        echo Forge:  Stopped
        del "%PID_DIR%\forge.pid"
    )
) else (
    echo Forge:  Stopped
)

if exist "%PID_DIR%\praxis.pid" (
    set /p PRAXIS_PID=<"%PID_DIR%\praxis.pid"
    tasklist /FI "PID eq !PRAXIS_PID!" 2>nul | find "!PRAXIS_PID!" >nul
    if !errorlevel!==0 (
        echo Praxis: Running (PID: !PRAXIS_PID!) on port %PRAXIS_PORT%
    ) else (
        echo Praxis: Stopped
        del "%PID_DIR%\praxis.pid"
    )
) else (
    echo Praxis: Stopped
)

echo.
exit /b 0

:usage
echo GEE System Management Script
echo.
echo Usage: %0 {start^|stop^|restart^|status^|logs^|forge-start^|forge-stop^|forge-restart^|praxis-start^|praxis-stop^|praxis-restart}
echo.
echo Commands:
echo   start         - Start both Forge and Praxis
echo   stop          - Stop both Forge and Praxis
echo   restart       - Restart both Forge and Praxis
echo   status        - Show status of both services
echo   logs          - Open log files in Notepad
echo.
echo Individual service commands:
echo   forge-start   - Start only Forge
echo   forge-stop    - Stop only Forge
echo   forge-restart - Restart only Forge
echo   praxis-start  - Start only Praxis
echo   praxis-stop   - Stop only Praxis
echo   praxis-restart- Restart only Praxis
echo.

:end
endlocal