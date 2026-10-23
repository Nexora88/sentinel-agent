@echo off
setlocal EnableExtensions
title MKAOS - Tek Tus Kurulum
cd /d "%~dp0"
echo.
echo  MKAOS / SENTINEL - Yerel Zeka Kurulumu
echo  --------------------------------------
echo  Bu kurulum interneti yalnizca Python paketlerini indirmek icin kullanir.
echo  Model agirliklari kaynak depoya dahil degildir ve ayri kurulmalidir.
echo.
set "PYEXE="
py -3.12 --version >nul 2>&1 && set "PYEXE=py -3.12"
if not defined PYEXE (
  echo HATA: Python 3.12 bulunamadi.
  echo Python 3.12 kurup bu dosyayi yeniden calistirin.
  echo https://www.python.org/downloads/
  pause
  exit /b 1
)
for /f "tokens=2 delims==" %%M in ('wmic computersystem get TotalPhysicalMemory /value 2^>nul ^| find "="') do set /a "RAMGB=%%M/1073741824"
if not defined RAMGB set "RAMGB=0"
echo Algilanan fiziksel RAM: %RAMGB% GB
echo.
echo Performans profili secin:
echo [1] 8 GB profili - dusuk bellek kullanimi, daha kucuk is yukleri
echo [2] 16 GB profili - daha buyuk baglam icin daha fazla bellek payi
echo Bu secim RAM eklemez; yalnizca MKAOS profil tercihini kaydeder.
set /p "PROFILE=Seciminiz (1/2) [1]: "
if "%PROFILE%"=="" set "PROFILE=1"
if "%PROFILE%"=="2" (set "PROFILE_NAME=16GB") else (set "PROFILE_NAME=8GB")
if %RAMGB% LSS 8 echo UYARI: Cihaz 8 GB altinda. Buyuk model veya yogun is yukleri bellek hatasi verebilir.
if not exist ".venv\Scripts\python.exe" (
  echo [1/4] Sanal ortam olusturuluyor...
  %PYEXE% -m venv .venv
  if errorlevel 1 goto :fail
)
echo [2/4] Paket yoneticisi hazirlaniyor...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail
echo [3/4] Uygulama bagimliliklari kuruluyor...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :fail
if not exist ".env" (
  copy ".env.example" ".env" >nul
  powershell -NoProfile -Command "$p=[Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(36)); Add-Content -LiteralPath '.env' -Value ('OWNER_PASSWORD=' + $p)"
)
findstr /b /c:"MKAOS_MEMORY_PROFILE=" ".env" >nul
if errorlevel 1 (echo MKAOS_MEMORY_PROFILE=%PROFILE_NAME%>>".env") else (powershell -NoProfile -Command "$p='.env'; $c=Get-Content $p; $c=$c -replace '^MKAOS_MEMORY_PROFILE=.*$', 'MKAOS_MEMORY_PROFILE=%PROFILE_NAME%'; Set-Content -Encoding utf8 $p $c")
echo [4/4] Kurulum tamamlandi.
echo Profil: %PROFILE_NAME%
echo.
echo Model dosyalari bu kurulumla indirilmez. Model ve uyumlu yerel motor olmadan sohbet kullanilamaz.
echo Uygulama yalnizca yerel bilgisayara baglanacak sekilde baslatiliyor...
set "PYTHONUTF8=1"
start "MKAOS" cmd /k ""%CD%\.venv\Scripts\python.exe" -m scripts.run web --host 127.0.0.1 --port 8000"
timeout /t 2 >nul
start "" "http://127.0.0.1:8000"
echo Bitti. .env ve OWNER_PASSWORD dosyasini paylasmayin.
pause
exit /b 0
:fail
echo.
echo Kurulum basarisiz. Yukaridaki hata mesajini kontrol edin.
pause
exit /b 1
