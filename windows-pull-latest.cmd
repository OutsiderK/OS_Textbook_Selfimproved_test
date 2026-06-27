@echo off
setlocal

cd /d "%~dp0"

where git >nul 2>nul
if errorlevel 1 (
  echo Git was not found.
  echo Install Git for Windows first: https://git-scm.com/download/win
  echo.
  pause
  exit /b 1
)

git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
  echo This folder is not a Git repository.
  echo Clone the repository first:
  echo git clone https://github.com/OutsiderK/OS_Textbook.git
  echo.
  pause
  exit /b 1
)

echo Updating textbook from origin/main...
echo.

git fetch origin
if errorlevel 1 goto failed

git switch main
if errorlevel 1 goto failed

git pull --ff-only origin main
if errorlevel 1 goto failed

echo.
echo Done. The textbook is up to date.
pause
exit /b 0

:failed
echo.
echo Update failed. If you changed files locally, save or commit them first, then try again.
pause
exit /b 1
