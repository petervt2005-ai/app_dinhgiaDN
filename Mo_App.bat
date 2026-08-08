@echo off
chcp 65001 >nul
title Vnstock App
echo ============================================
echo   Vnstock App - Dang khoi dong...
echo ============================================
echo.

REM Kiem tra Python co san khong
where python >nul 2>nul
if errorlevel 1 (
    echo [LOI] Khong tim thay Python tren may nay.
    echo Hay cai dat Python tu https://www.python.org/downloads/
    echo Sau khi cai, mo lai file nay.
    pause
    exit /b 1
)

REM Kiem tra va cai vnstock neu chua co
python -c "import vnstock" >nul 2>nul
if errorlevel 1 (
    echo Chua co thu vien vnstock. Dang cai dat, vui long doi...
    pip install -U vnstock
    if errorlevel 1 (
        echo [LOI] Cai dat vnstock khong thanh cong. Kiem tra ket noi Internet.
        pause
        exit /b 1
    )
)

echo Dang mo giao dien app...
python "%~dp0vnstock_app.py"

if errorlevel 1 (
    echo.
    echo [LOI] App gap loi khi chay. Xem chi tiet loi phia tren.
    pause
)
