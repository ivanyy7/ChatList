# Публикация ChatList на GitHub Release и GitHub Pages

Пошаговая инструкция для размещения приложения в релизах и лендинга на GitHub Pages.

---

## Часть 1. Подготовка к релизу

### Шаг 1.1. Обновите версию (если нужно)

Отредактируйте `version.py` и измените `__version__`:

```python
__version__ = "1.0.0"  # Новая версия
```

### Шаг 1.2. Закоммитьте все изменения

```powershell
git add .
git status
git commit -m "Подготовка к релизу 1.0.0"
```

### Шаг 1.3. Создайте тег версии

```powershell
git tag -a v1.0.0 -m "Релиз 1.0.0"
```

### Шаг 1.4. Отправьте изменения и тег на GitHub

```powershell
git push origin main
git push origin v1.0.0
```

---

## Часть 2. GitHub Release (автоматически через Actions)

### Шаг 2.1. Проверьте workflow

В репозитории должен быть файл `.github/workflows/release.yml`. При пуше тега он:

1. Собирает exe через PyInstaller
2. Создаёт установщик через Inno Setup
3. Создаёт релиз с прикреплённым `ChatList_X.X.X_Setup.exe`

### Шаг 2.2. Запуск сборки

1. Выполните шаги 1.1–1.4 (создание и пуш тега)
2. Откройте репозиторий на GitHub
3. Вкладка **Actions** → выберите запущенный workflow **Build and Release**
4. Дождитесь завершения (зелёная галочка)

### Шаг 2.3. Проверка релиза

1. Вкладка **Releases** (или справа в блоке «Releases»)
2. Должен появиться релиз `v1.0.0` с установщиком

### Шаг 2.4. Ручной релиз (если Actions не настроены)

1. **Releases** → **Create a new release**
2. **Choose a tag**: `v1.0.0` или создайте новый
3. **Release title**: `ChatList 1.0.0`
4. **Describe this release**: краткое описание изменений
5. Прикрепите файл `dist\ChatList_1.0.0_Setup.exe` (собранный локально через `.\build_installer.ps1`)
6. **Publish release**

---

## Часть 3. GitHub Pages (лендинг)

### Шаг 3.1. Включите GitHub Pages

1. Репозиторий → **Settings** → **Pages**
2. **Source**: `Deploy from a branch`
3. **Branch**: `main` (или `master`)
4. **Folder**: `/docs`
5. **Save**

### Шаг 3.2. Проверка

Через 1–2 минуты страница будет доступна по адресу:

```
https://<ваш-username>.github.io/ChatList/
```

Например: `https://ivanyy7.github.io/ChatList/`

### Шаг 3.3. Обновление лендинга

Лендинг лежит в `docs/index.html`. Если ваш репозиторий не `ivanyy7/ChatList`, замените ссылки в файле на ваш `username/repo`.

```powershell
git add docs/index.html
git commit -m "Обновление лендинга"
git push origin main
```

GitHub Pages обновится автоматически.

---

## Часть 4. Чек-лист перед релизом

- [ ] Версия в `version.py` обновлена
- [ ] README актуален
- [ ] `.env.example` есть в репозитории
- [ ] Все изменения закоммичены
- [ ] Тег создан и запушен
- [ ] GitHub Actions успешно отработал (если используется)
- [ ] Release создан с установщиком
- [ ] GitHub Pages включён и открывается

---

## Быстрая шпаргалка

```powershell
# Полный цикл релиза
# 1. Обновить version.py
# 2. Закоммитить
git add .
git commit -m "Релиз 1.0.0"

# 3. Создать тег и запушить
git tag -a v1.0.0 -m "Релиз 1.0.0"
git push origin main
git push origin v1.0.0

# 4. Проверить Actions и Releases на GitHub
# 5. Проверить GitHub Pages
```
