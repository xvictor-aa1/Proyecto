@echo off
title Instalador Automático del Sistema
echo ==============================================
echo  Instalador Automático del Sistema
echo ==============================================
echo.

:: Verificar si Python ya está instalado (buscando python.exe)
py --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Python ya esta instalado. Omitiendo instalacion...
) else (
    echo [INFO] Python no encontrado. Iniciando descarga e instalacion...
    echo.

    :: Descargar instalador de Python
    set PYTHON_URL=https://www.python.org/ftp/python/3.13.5/python-3.13.5-amd64.exe
    set INSTALLER_NAME=python_installer.exe
    echo Descargando instalador desde %PYTHON_URL% ...
    powershell -Command "Invoke-WebRequest -Uri %PYTHON_URL% -OutFile %INSTALLER_NAME%"
    if %errorlevel% neq 0 (
        echo [ERROR] Fallo al descargar Python.
        pause
        exit /b 1
    )
    echo [OK] Descarga completada.

    :: 2. Instalar Python en modo silencioso
    echo Instalando Python. Por favor, espere...
    %INSTALLER_NAME% /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    if %errorlevel% neq 0 (
        echo [ERROR] Fallo en la instalacion silenciosa de Python.
        pause
        exit /b 1
    )
    echo [OK] Python instalado correctamente.
    echo Limpiando instalador...
    del %INSTALLER_NAME%
    echo.
)

:: Actualizar pip e instalar los módulos
echo Actualizando pip...
py -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo [ERROR] No se pudo actualizar pip.
    pause
    exit /b 1
)

py -m pip install mysql.connector
if %errorlevel% neq 0 (
    echo [ERROR] Fallo la instalacion de Flask.
    pause
    exit /b 1
)

py -m pip install flask
if %errorlevel% neq 0 (
    echo [ERROR] Fallo la instalacion de Flask.
    pause
    exit /b 1
)

py -m pip install reportlab
if %errorlevel% neq 0 (
    echo [ERROR] Fallo la instalacion de ReportLab.
    pause
    exit /b 1
)

py -m pip install pillow
if %errorlevel% neq 0 (
    echo [ERROR] Fallo la instalacion de Pillow.
    pause
    exit /b 1
)

echo.
echo ==============================================
echo  Instalacion completada con exito.
echo ==============================================
pause