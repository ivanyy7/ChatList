@echo off
chcp 65001 >nul
echo Установка зависимостей...
pip install -r requirements.txt

echo.
echo Создание исполняемого файла ChatList...
pyinstaller --noconfirm ChatList.spec

if exist dist\ChatList.exe (
    echo.
    echo Готово! Исполняемый файл: dist\ChatList.exe
) else (
    echo.
    echo Ошибка сборки. Закройте ChatList.exe, если он запущен, и повторите.
)
pause
