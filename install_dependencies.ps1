# Скрипт установки зависимостей для ChatList
Write-Host "Установка зависимостей для ChatList..." -ForegroundColor Green

# Проверка наличия pip
try {
    $pipVersion = python -m pip --version
    Write-Host "Найден pip: $pipVersion" -ForegroundColor Green
} catch {
    Write-Host "Ошибка: pip не найден. Убедитесь, что Python установлен." -ForegroundColor Red
    exit 1
}

# Установка пакетов
Write-Host "`nУстановка requests..." -ForegroundColor Yellow
python -m pip install --user requests

Write-Host "`nУстановка python-dotenv..." -ForegroundColor Yellow
python -m pip install --user python-dotenv

Write-Host "`nПроверка установленных пакетов..." -ForegroundColor Yellow
python -m pip list | Select-String -Pattern "requests|dotenv|PyQt5"

Write-Host "`nУстановка завершена!" -ForegroundColor Green
Write-Host "Теперь можно запустить приложение: python main.py" -ForegroundColor Cyan
