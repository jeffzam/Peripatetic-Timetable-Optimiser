@echo off
setlocal
cd /d "%~dp0"

set "PLANNER_PYTHONW="
for /f "delims=" %%P in ('where pythonw.exe 2^>nul') do if not defined PLANNER_PYTHONW set "PLANNER_PYTHONW=%%P"

if not defined PLANNER_PYTHONW (
    for /d %%D in ("%LocalAppData%\Programs\Python\Python*") do (
        if exist "%%~fD\pythonw.exe" set "PLANNER_PYTHONW=%%~fD\pythonw.exe"
    )
)

if not defined PLANNER_PYTHONW goto python_missing

start "" "%PLANNER_PYTHONW%" "%~dp0run.py"
exit /b 0

:python_missing
echo Python could not be found on this computer.
echo Please install Python with the Tcl/Tk option, then try again.
pause
exit /b 1
