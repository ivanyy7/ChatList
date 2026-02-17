@echo off
echo Установка PyInstaller...
pip install pyinstaller

echo Создание исполняемого файла...
pyinstaller --onefile --windowed --name="PyQtApp" main.py

echo Готово! Исполняемый файл находится в папке dist\PyQtApp.exe
pause
