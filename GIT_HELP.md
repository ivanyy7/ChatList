# Помощь по работе с Git

## Текущая ситуация

У вас есть локальные изменения, которые не синхронизированы с GitHub.

## Команды для синхронизации

### Проверить статус:
```powershell
git status
```

### Отправить изменения на GitHub:
```powershell
git push origin main
```

### Получить изменения с GitHub:
```powershell
git pull origin main
```

## Если возникают проблемы с подключением

### Вариант 1: Проверить интернет-соединение
```powershell
ping github.com
```

### Вариант 2: Использовать SSH вместо HTTPS (если настроен SSH ключ)
```powershell
git remote set-url origin git@github.com:ivanyy7/ChatList.git
```

### Вариант 3: Настроить прокси (если требуется)
```powershell
git config --global http.proxy http://proxy.example.com:8080
git config --global https.proxy https://proxy.example.com:8080
```

### Вариант 4: Отключить проверку SSL (только для тестирования)
```powershell
git config --global http.sslVerify false
```

## Полезные команды

### Просмотр истории коммитов:
```powershell
git log --oneline
```

### Просмотр изменений:
```powershell
git diff
```

### Отмена последнего коммита (сохраняя изменения):
```powershell
git reset --soft HEAD~1
```
