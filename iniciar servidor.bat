@echo off
setlocal enabledelayedexpansion

:: Rutas
set "VENV_ROOT=%~dp0python_local"
set "PYTHON_EXE=%VENV_ROOT%\Scripts\python.exe"
set "APP_SCRIPT=%~dp0app.py"

:: Verificar entorno virtual
if not exist "%PYTHON_EXE%" (
    echo [ERROR] No se encontro el entorno virtual en: %VENV_ROOT%
    echo Asegurate de que la carpeta "python_local" existe y contiene Scripts\python.exe
    pause
    exit /b 1
)

:: Verificar app.py
if not exist "%APP_SCRIPT%" (
    echo [ERROR] No se encontro el archivo app.py en: %~dp0
    pause
    exit /b 1
)

:menu
cls
echo ========================================================
echo   SISTEMA DE RECEPCIÓN DE EQUIPOS - Alcaldia Carlos Arvelo
echo ========================================================
echo   1. Iniciar sistema
echo   2. Realizar backup
echo   3. Salir
echo ========================================================
set /p opcion="Elige una opcion (1-3): "

if "%opcion%"=="1" goto iniciar_sistema
if "%opcion%"=="2" goto menu_backup
if "%opcion%"=="3" goto fin
echo Opcion no valida. Intentalo de nuevo.
pause
goto menu

:menu_backup
cls
echo ========================================================
echo   OPCIONES DE BACKUP
echo ========================================================
echo   1. Backup general (configuracion + BD + codigo)
echo   2. Solo configuracion (config.py)
echo   3. Solo base de datos
echo   4. Solo codigo del sistema (archivos fuente)
echo   5. Volver al menu principal
echo ========================================================
set /p tipo="Elige una opcion de backup (1-5): "

if "%tipo%"=="1" (
    echo Ejecutando backup general...
    "%PYTHON_EXE%" "%APP_SCRIPT%" -backup general
    pause
    goto menu
)
if "%tipo%"=="2" (
    echo Ejecutando backup de configuracion...
    "%PYTHON_EXE%" "%APP_SCRIPT%" -backup config
    pause
    goto menu
)
if "%tipo%"=="3" (
    echo Ejecutando backup de base de datos...
    "%PYTHON_EXE%" "%APP_SCRIPT%" -backup database
    pause
    goto menu
)
if "%tipo%"=="4" (
    echo Ejecutando backup de codigo del sistema...
    "%PYTHON_EXE%" "%APP_SCRIPT%" -backup integridad
    pause
    goto menu
)
if "%tipo%"=="5" goto menu
echo Opcion no valida.
pause
goto menu_backup

:iniciar_sistema
cls
echo Iniciando el sistema de reportes...
"%PYTHON_EXE%" "%APP_SCRIPT%"
goto menu

:fin
cls
echo Saliendo del sistema...
pause
endlocal
exit /b 0