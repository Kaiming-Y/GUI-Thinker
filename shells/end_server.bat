@echo off
setlocal enabledelayedexpansion

REM Define hardcoded port numbers

set "port_planner_critic=5001"
set "port_gui_parser=5002"
set "port_step_check=5003"
set "port_actor=5004"
set "port_actorcritic=5005"

REM Check input parameters
if "%~1"=="" (
    set stop_all=1
) else (
    set stop_all=0
)

REM Determine which ports to stop based on input parameters
if "%stop_all%"=="1" (
    set ports=%port_gui_parser% %port_actor% %port_step_check% %port_actorcritic% %port_planner_critic%
) else (
    set ports=%*
)

REM Stop processes based on ports
for %%p in (%ports%) do (
    @REM for /f "tokens=5" %%a in ('netstat -aon ^| findstr :%%p ^| findstr LISTENING') do (
    for /f "tokens=5" %%a in ('%SystemRoot%\System32\netstat.exe -aon ^| %SystemRoot%\System32\findstr.exe ":%%p " ^| %SystemRoot%\System32\findstr.exe LISTENING') do (
        @REM taskkill /PID %%a /T /F
        %SystemRoot%\System32\taskkill.exe /PID %%a /T /F
    )
)

echo All specified servers have been stopped.
