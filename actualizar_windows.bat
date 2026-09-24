@echo off
rem Actualiza la tienda a la última versión de GitHub: doble clic en este archivo.
rem Requiere Python 3.10 o más reciente instalado desde https://www.python.org
chcp 65001 >nul
cd /d "%~dp0"

echo Antes de actualizar, cierra la Tienda si está abierta.
pause

rem "py" es el lanzador que instala python.org; se prefiere porque el
rem "python" de la Microsoft Store puede ser solo un acceso a la tienda
where py >nul 2>nul
if errorlevel 1 (set "PYTHON=python") else (set "PYTHON=py -3")

%PYTHON% --version >nul 2>nul
if errorlevel 1 (
    echo.
    echo No se encontró Python.
    echo Instálalo desde https://www.python.org/downloads/ marcando la casilla
    echo "Add python.exe to PATH" y vuelve a abrir este archivo.
    echo.
    pause
    exit /b 1
)

rem Windows lee los .bat de a poco mientras los ejecuta, y la actualización
rem puede reemplazar este mismo archivo. Por eso lo que falta va en un solo
rem bloque: Windows lo lee completo antes de empezar y no se confunde después
(
    %PYTHON% actualizar.py %*
    echo.
    pause
    exit /b
)
