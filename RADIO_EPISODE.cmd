@echo off
setlocal
REM Windows launcher. Run from any current working directory.
set "ROOT=%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 --version >nul 2>nul
  if not errorlevel 1 (
    py -3 "%ROOT%tools\episode_operator.py" %*
    exit /b %ERRORLEVEL%
  )
)
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python or run tools\episode_operator.py directly.
  exit /b 1
)
python "%ROOT%tools\episode_operator.py" %*
exit /b %ERRORLEVEL%
