# Сборка установщика ChatList
# Версия берётся из version.py, используется PyInstaller и Inno Setup

$ErrorActionPreference = "Stop"

Write-Host "ChatList — сборка установщика" -ForegroundColor Green
Write-Host ""

# 1. Получить версию из version.py
$version = python -c "from version import __version__; print(__version__)"
if (-not $version) {
    Write-Host "Ошибка: не удалось получить версию из version.py" -ForegroundColor Red
    exit 1
}
Write-Host "Версия: $version" -ForegroundColor Cyan

# 2. Собрать исполняемый файл
Write-Host ""
Write-Host "Сборка exe..." -ForegroundColor Yellow
pyinstaller --noconfirm ChatList.spec
if (-not $?) {
    Write-Host "Ошибка сборки PyInstaller" -ForegroundColor Red
    exit 1
}

# 3. Проверить наличие exe
if (-not (Test-Path "dist\ChatList.exe")) {
    Write-Host "Ошибка: dist\ChatList.exe не найден" -ForegroundColor Red
    exit 1
}

# 4. Собрать установщик Inno Setup
Write-Host ""
Write-Host "Сборка установщика Inno Setup..." -ForegroundColor Yellow
$isccPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $isccPath)) {
    $isccPath = "C:\Program Files\Inno Setup 6\ISCC.exe"
}
if (-not (Test-Path $isccPath)) {
    Write-Host "Ошибка: Inno Setup не найден. Установите Inno Setup 6." -ForegroundColor Red
    Write-Host "Скачать: https://jrsoftware.org/isdl.php" -ForegroundColor Gray
    exit 1
}

& $isccPath "/DMyAppVersion=$version" "ChatList.iss"
if (-not $?) {
    Write-Host "Ошибка сборки установщика" -ForegroundColor Red
    exit 1
}

Write-Host ""
$setupName = "ChatList_${version}_Setup.exe"
if (Test-Path "dist\$setupName") {
    Write-Host "Готово! Установщик: dist\$setupName" -ForegroundColor Green
} else {
    Write-Host "Готово! Установщик в папке dist\" -ForegroundColor Green
}
