@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "APP_ONLY=0"
if /i "%~1"=="--app-only" set "APP_ONLY=1"
if not "%~1"=="" if "%APP_ONLY%"=="0" (
  echo Uso: build.bat [--app-only]
  exit /b 1
)

rem Build tools are needed only by the developer. Users install the bundled EXE.
where py >nul 2>nul
if errorlevel 1 (
  echo Instale Python 3.12 de python.org com o Python Launcher para compilar.
  exit /b 1
)

set "ISCC="
if "%APP_ONLY%"=="0" (
  for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do if not defined ISCC set "ISCC=%%I"
  if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
  if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
)
if "%APP_ONLY%"=="0" if not defined ISCC (
  echo Instale Inno Setup 6.3 ou superior: https://jrsoftware.org/isinfo.php
  echo Para gerar somente a distribuicao portatil, execute build.bat --app-only.
  exit /b 1
)

if not exist .venv\Scripts\python.exe (
  py -3.12 -m venv .venv
  if errorlevel 1 exit /b 1
)
.venv\Scripts\python.exe -c "import struct, sys; assert sys.version_info[:2] == (3, 12), 'Use Python 3.12'; assert struct.calcsize('P') == 8, 'Use Python 64 bits'"
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m pip install --disable-pip-version-check --no-input -r requirements-lock.txt
if errorlevel 1 exit /b 1

set "QT_QPA_PLATFORM=offscreen"
.venv\Scripts\python.exe -m pytest -q
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --noupx --windowed --onedir --name Studytonks --icon app\assets\studytonks.ico --add-data "app\assets;app\assets" main.py
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe packaging\check_runtime.py
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe packaging\smoke_bundle.py
if errorlevel 1 exit /b 1

set "APP_VERSION="
for /f "delims=" %%V in ('.venv\Scripts\python.exe -c "import pathlib,tomllib; print(tomllib.loads(pathlib.Path('pyproject.toml').read_text(encoding='utf-8'))['project']['version'])"') do set "APP_VERSION=%%V"
if not defined APP_VERSION exit /b 1
if "%APP_ONLY%"=="1" goto portable

"%ISCC%" "/DAppVersion=%APP_VERSION%" packaging\Studytonks.iss
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe packaging\make_artifacts.py
if errorlevel 1 exit /b 1
goto finished

:portable
.venv\Scripts\python.exe packaging\make_artifacts.py --app-only
if errorlevel 1 exit /b 1

:finished
echo.
echo Arquivos prontos em dist\release:
if "%APP_ONLY%"=="0" echo   Studytonks-Setup.exe - instalador com Python, Qt e dependencias incluidos
echo   Studytonks-Portable.zip - extrair a pasta inteira e abrir Studytonks.exe
echo   Studytonks-Source.zip - codigo-fonte do commit Git atual
echo   SHA256SUMS.txt - verificacao de integridade
echo O usuario final nao precisa instalar Python, pip ou bibliotecas.
echo Dados pessoais permanecem em %%APPDATA%%\Studytonks, fora dos binarios.
endlocal
