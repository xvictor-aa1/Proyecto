@echo off
title Sistema de Reportes v5.0 - Alcaldia Carlos Arvelo
cd /d "%~dp0"
echo.
echo =====================================================
echo   SISTEMA DE REPORTES v5.0 - MODO RED
echo   Alcaldia Bolivariana del Municipio Carlos Arvelo
echo =====================================================
echo.
echo  Acceso LOCAL:   http://localhost:5000
echo.
echo  Acceso en RED:  Abre CMD y escribe "ipconfig"
echo                  Busca "Direccion IPv4"
echo                  Usa esa IP en los otros equipos
echo                  Ejemplo: http://192.168.1.15:5000
echo.
echo  NO CIERRES ESTA VENTANA mientras uses el sistema.
echo =====================================================
echo.
start "" http://localhost:5000
py app.py
pause
