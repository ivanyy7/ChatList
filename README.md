# Минимальное PyQt приложение

Простое приложение с графическим интерфейсом на PyQt5.

## Установка зависимостей

```powershell
pip install -r requirements.txt
```

## Запуск

```powershell
python main.py
```

## Создание исполняемого файла

```powershell
pyinstaller --onefile --windowed --name="PyQtApp" main.py
```

Исполняемый файл будет создан в папке `dist` с именем `PyQtApp.exe`.

## Описание

Приложение создает окно с меткой и кнопкой. При нажатии на кнопку текст метки изменяется между двумя фразами.
