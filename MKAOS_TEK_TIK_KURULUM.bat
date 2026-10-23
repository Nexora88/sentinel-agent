@echo off
setlocal EnableExtensions
title MKAOS - Tek Indirmeli Kurulum
set "ROOT=%LOCALAPPDATA%\MKAOS"
set "ZIP=%TEMP%\mkaos-main.zip"
set "STAGE=%ROOT%\source"
echo.
echo MKAOS tek indirmeli kurulum baslatiliyor.
echo Kaynak: https://github.com/Nexora88/sentinel-agent
echo Hedef: %ROOT%
echo.
echo Bu dosya resmi GitHub deposundan kaynak indirip yerel kurulum betigini calistiracak.
echo Yonetici yetkisi istemez. Devam etmeden once kaynak kodu incelemeniz onerilir.
choice /C EH /N /M "Devam edilsin mi? [E/H] "
if errorlevel 2 exit /b 0
where py >nul 2>&1
if errorlevel 1 (
  echo HATA: Python 3.12 launcher bulunamadi.
  echo Once https://www.python.org/downloads/ adresinden Python 3.12 kurun.
  pause
  exit /b 1
)
py -3.12 --version >nul 2>&1
if errorlevel 1 (
  echo HATA: Python 3.12 kurulu degil.
  echo Once https://www.python.org/downloads/ adresinden Python 3.12 kurun.
  pause
  exit /b 1
)
if not exist "%ROOT%" mkdir "%ROOT%"
if errorlevel 1 goto :fail
echo [1/3] Resmi kaynak ZIP indiriliyor...
powershell -NoProfile -Command "$ErrorActionPreference='Stop'; Invoke-WebRequest -Uri 'https://github.com/Nexora88/sentinel-agent/archive/refs/heads/main.zip' -OutFile '%ZIP%'"
if errorlevel 1 goto :fail
echo [2/3] Kaynak dosyalar aciliyor...
if not exist "%STAGE%" mkdir "%STAGE%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Expand-Archive -LiteralPath '%ZIP%' -DestinationPath '%ROOT%\unpack' -Force; $src=Join-Path '%ROOT%\unpack' 'sentinel-agent-main'; if (!(Test-Path $src)) { throw 'GitHub ZIP icinde sentinel-agent-main klasoru bulunamadi.' }; if (!(Test-Path '%STAGE%')) { New-Item -ItemType Directory -Path '%STAGE%' | Out-Null }; Get-ChildItem -LiteralPath $src -Force | Where-Object { $_.Name -notin @('memory','.venv','models') } | Copy-Item -Destination '%STAGE%' -Recurse -Force; if (!(Test-Path (Join-Path '%STAGE%' 'memory'))) { New-Item -ItemType Directory -Path (Join-Path '%STAGE%' 'memory') | Out-Null }; if (!(Test-Path (Join-Path '%STAGE%' 'models'))) { New-Item -ItemType Directory -Path (Join-Path '%STAGE%' 'models') | Out-Null }; Remove-Item -LiteralPath '%ROOT%\unpack' -Recurse -Force; Remove-Item -LiteralPath '%ZIP%' -Force"
if errorlevel 1 goto :fail
echo [3/3] Yerel kurulum baslatiliyor...
call "%STAGE%\INSTALL_MKAOS_WINDOWS.bat"
exit /b %errorlevel%
:fail
echo.
echo Kurulum basarisiz. Internet baglantisini ve Windows PowerShell erisimini kontrol edin.
if exist "%ZIP%" del "%ZIP%" >nul 2>&1
pause
exit /b 1
