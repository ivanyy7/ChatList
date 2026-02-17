# Схема базы данных ChatList

## Общая информация

База данных: SQLite  
Файл БД: `chatlist.db` (создаётся автоматически при первом запуске)

## Таблицы

### 1. Таблица `prompts` (Промпты)

Хранит все введённые пользователем промпты.

| Поле | Тип | Описание | Ограничения |
|------|-----|----------|-------------|
| `id` | INTEGER | Первичный ключ, автоинкремент | PRIMARY KEY, AUTOINCREMENT |
| `date` | TEXT | Дата и время создания промпта | NOT NULL, формат: ISO8601 (YYYY-MM-DD HH:MM:SS) |
| `prompt` | TEXT | Текст промпта | NOT NULL |
| `tags` | TEXT | Теги для категоризации (через запятую) | Может быть NULL |

**Индексы:**
- `idx_prompts_date` на поле `date` (для быстрой сортировки по дате)
- `idx_prompts_tags` на поле `tags` (для поиска по тегам)

**Пример записи:**
```sql
INSERT INTO prompts (date, prompt, tags) 
VALUES ('2026-02-17 10:30:00', 'Объясни квантовую физику простыми словами', 'наука, физика');
```

---

### 2. Таблица `models` (Модели нейросетей)

Хранит конфигурацию доступных моделей нейросетей.

| Поле | Тип | Описание | Ограничения |
|------|-----|----------|-------------|
| `id` | INTEGER | Первичный ключ, автоинкремент | PRIMARY KEY, AUTOINCREMENT |
| `name` | TEXT | Название модели (например, "GPT-4", "DeepSeek") | NOT NULL, UNIQUE |
| `api_url` | TEXT | URL API для отправки запросов | NOT NULL |
| `api_id` | TEXT | Идентификатор переменной окружения с API-ключом (например, "OPENAI_API_KEY") | NOT NULL |
| `is_active` | INTEGER | Флаг активности модели (1 - активна, 0 - неактивна) | NOT NULL, DEFAULT 1, CHECK(is_active IN (0, 1)) |

**Индексы:**
- `idx_models_active` на поле `is_active` (для быстрого получения активных моделей)
- `idx_models_name` на поле `name` (уникальный индекс)

**Пример записи:**
```sql
INSERT INTO models (name, api_url, api_id, is_active) 
VALUES ('GPT-4', 'https://api.openai.com/v1/chat/completions', 'OPENAI_API_KEY', 1);
```

**Примечание:** Сами API-ключи хранятся в файле `.env` в формате:
```
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=...
GROQ_API_KEY=...
```

---

### 3. Таблица `results` (Результаты)

Хранит сохранённые пользователем результаты ответов моделей.

| Поле | Тип | Описание | Ограничения |
|------|-----|----------|-------------|
| `id` | INTEGER | Первичный ключ, автоинкремент | PRIMARY KEY, AUTOINCREMENT |
| `prompt_id` | INTEGER | Ссылка на промпт из таблицы `prompts` | NOT NULL, FOREIGN KEY REFERENCES prompts(id) ON DELETE CASCADE |
| `model_name` | TEXT | Название модели, которая дала ответ | NOT NULL |
| `response_text` | TEXT | Текст ответа модели | NOT NULL |
| `created_at` | TEXT | Дата и время сохранения результата | NOT NULL, формат: ISO8601 (YYYY-MM-DD HH:MM:SS) |

**Индексы:**
- `idx_results_prompt_id` на поле `prompt_id` (для быстрого поиска результатов по промпту)
- `idx_results_model_name` на поле `model_name` (для фильтрации по модели)
- `idx_results_created_at` на поле `created_at` (для сортировки по дате)

**Пример записи:**
```sql
INSERT INTO results (prompt_id, model_name, response_text, created_at) 
VALUES (1, 'GPT-4', 'Квантовая физика изучает поведение частиц...', '2026-02-17 10:35:00');
```

---

### 4. Таблица `settings` (Настройки)

Хранит настройки приложения в формате ключ-значение.

| Поле | Тип | Описание | Ограничения |
|------|-----|----------|-------------|
| `id` | INTEGER | Первичный ключ, автоинкремент | PRIMARY KEY, AUTOINCREMENT |
| `key` | TEXT | Ключ настройки | NOT NULL, UNIQUE |
| `value` | TEXT | Значение настройки | Может быть NULL |

**Индексы:**
- `idx_settings_key` на поле `key` (уникальный индекс для быстрого поиска)

**Примеры записей:**
```sql
INSERT INTO settings (key, value) VALUES ('theme', 'dark');
INSERT INTO settings (key, value) VALUES ('default_timeout', '30');
INSERT INTO settings (key, value) VALUES ('auto_save', 'false');
```

**Возможные ключи настроек:**
- `theme` - тема интерфейса (dark/light)
- `default_timeout` - таймаут запросов по умолчанию (секунды)
- `auto_save` - автоматическое сохранение результатов (true/false)
- `log_level` - уровень логирования (DEBUG/INFO/WARNING/ERROR)
- `export_format` - формат экспорта по умолчанию (markdown/json)

---

## Связи между таблицами

```
prompts (1) ──────< (N) results
   │                    │
   │                    └─ model_name (ссылка на models.name)
   │
   └─ id (PK)
```

- Один промпт может иметь множество результатов (`prompt_id` в `results` ссылается на `id` в `prompts`)
- При удалении промпта все связанные результаты удаляются автоматически (ON DELETE CASCADE)
- `model_name` в таблице `results` хранит название модели как строку (не внешний ключ) для гибкости

---

## SQL-скрипт создания таблиц

```sql
-- Таблица промптов
CREATE TABLE IF NOT EXISTS prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    prompt TEXT NOT NULL,
    tags TEXT
);

CREATE INDEX IF NOT EXISTS idx_prompts_date ON prompts(date);
CREATE INDEX IF NOT EXISTS idx_prompts_tags ON prompts(tags);

-- Таблица моделей
CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    api_url TEXT NOT NULL,
    api_id TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_models_active ON models(is_active);
CREATE INDEX IF NOT EXISTS idx_models_name ON models(name);

-- Таблица результатов
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id INTEGER NOT NULL,
    model_name TEXT NOT NULL,
    response_text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_results_prompt_id ON results(prompt_id);
CREATE INDEX IF NOT EXISTS idx_results_model_name ON results(model_name);
CREATE INDEX IF NOT EXISTS idx_results_created_at ON results(created_at);

-- Таблица настроек
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key);
```

---

## Временная таблица результатов

Временная таблица результатов **НЕ** хранится в SQLite. Она существует только в памяти приложения (Python структура данных) и содержит:

- `model_name` - название модели
- `response_text` - текст ответа
- `selected` - флаг выбора (boolean)
- `status` - статус запроса (pending/success/error)

Эта таблица создаётся при отправке запроса и удаляется при:
- Сохранении выбранных результатов в БД
- Очистке результатов пользователем
- Вводе нового промпта
