@echo off
rem Instala la tienda en Windows: doble clic en este archivo.
rem Requiere Python 3.10 o más reciente instalado desde https://www.python.org
chcp 65001 >nul
cd /d "%~dp0"

rem "py" es el lanzador que instala python.org; se prefiere porque el
rem "python" de la Microsoft Store puede ser solo un acceso a la tienda
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 instalar.py
) else (
    python --version >nul 2>nul
    if errorlevel 1 (
        echo.
        echo No se encontró Python.
        echo Instálalo desde https://www.python.org/downloads/ marcando la casilla
        echo "Add python.exe to PATH" y vuelve a abrir este archivo.
    ) else (
        python instalar.py
    )
)

echo.
pause
