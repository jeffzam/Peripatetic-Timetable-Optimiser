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

for %%F in ("%PLANNER_PYTHONW%") do set "PLANNER_PYTHON=%%~dpFpython.exe"
if not exist "%PLANNER_PYTHON%" goto python_missing

"%PLANNER_PYTHON%" -c "import openpyxl" >nul 2>&1
if errorlevel 1 (
    echo Preparing Excel support for the Peripatetic Timetable Planner...
    "%PLANNER_PYTHON%" -m pip install -r "%~dp0requirements.txt"
    if errorlevel 1 goto dependency_missing
)

start "" "%PLANNER_PYTHONW%" "%~dp0run.py"
exit /b 0

:dependency_missing
echo.
echo Excel support could not be installed.
echo Check the internet connection, then double-click START PLANNER again.
pause
exit /b 1

:python_missing
echo Python could not be found on this computer.
echo Please install Python with the Tcl/Tk option, then try again.
pause
exit /b 1
