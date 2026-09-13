@echo off
setlocal

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_and_test.ps1" %*
set "CROSSFEEDING_EXIT_CODE=%ERRORLEVEL%"

if not "%CROSSFEEDING_EXIT_CODE%"=="0" (
  echo.
  echo Cross-feeding Windows testing stopped with an error.
  echo Please copy the complete terminal output when reporting the problem.
) else (
  echo.
  echo Cross-feeding Windows testing completed successfully.
)

echo.
pause
exit /b %CROSSFEEDING_EXIT_CODE%
