"""
Модуль для работы с базой данных SQLite.
Инкапсулирует все операции с БД.
"""
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from config import get_database_path


DB_PATH = get_database_path()


def get_connection():
    """Создать соединение с базой данных."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
    return conn


def init_database():
    """
    Инициализация базы данных: создание файла БД и всех таблиц.
    Проверяет существование БД и создаёт её при первом запуске.
    """
    if not os.path.exists(DB_PATH):
        # Создаём файл БД
        conn = get_connection()
        cursor = conn.cursor()
        
        # Таблица промптов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                prompt TEXT NOT NULL,
                tags TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prompts_date ON prompts(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prompts_tags ON prompts(tags)")
        
        # Таблица моделей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                api_url TEXT NOT NULL,
                api_id TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1))
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_models_active ON models(is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_models_name ON models(name)")
        
        # Таблица результатов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_id INTEGER NOT NULL,
                model_name TEXT NOT NULL,
                response_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_prompt_id ON results(prompt_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_model_name ON results(model_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_created_at ON results(created_at)")
        
        # Таблица настроек
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key)")
        
        conn.commit()
        conn.close()


# ==================== CRUD операции для таблицы prompts ====================

def create_prompt(prompt: str, tags: Optional[str] = None) -> int:
    """
    Создать новый промпт.
    
    Args:
        prompt: Текст промпта
        tags: Теги через запятую (опционально)
    
    Returns:
        ID созданного промпта
    """
    conn = get_connection()
    cursor = conn.cursor()
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute(
        "INSERT INTO prompts (date, prompt, tags) VALUES (?, ?, ?)",
        (date, prompt, tags)
    )
    prompt_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return prompt_id


def get_all_prompts() -> List[Dict]:
    """Получить все промпты."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prompts ORDER BY date DESC")
    prompts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return prompts


def get_prompt_by_id(prompt_id: int) -> Optional[Dict]:
    """
    Получить промпт по ID.
    
    Args:
        prompt_id: ID промпта
    
    Returns:
        Словарь с данными промпта или None
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_prompt(prompt_id: int, prompt: str, tags: Optional[str] = None) -> bool:
    """
    Обновить промпт.
    
    Args:
        prompt_id: ID промпта
        prompt: Новый текст промпта
        tags: Новые теги
    
    Returns:
        True если обновление успешно, False иначе
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE prompts SET prompt = ?, tags = ? WHERE id = ?",
        (prompt, tags, prompt_id)
    )
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def delete_prompt(prompt_id: int) -> bool:
    """
    Удалить промпт.
    
    Args:
        prompt_id: ID промпта
    
    Returns:
        True если удаление успешно, False иначе
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def search_prompts(query: str) -> List[Dict]:
    """
    Поиск промптов по тексту или тегам.
    
    Args:
        query: Поисковый запрос
    
    Returns:
        Список найденных промптов
    """
    conn = get_connection()
    cursor = conn.cursor()
    search_term = f"%{query}%"
    cursor.execute(
        "SELECT * FROM prompts WHERE prompt LIKE ? OR tags LIKE ? ORDER BY date DESC",
        (search_term, search_term)
    )
    prompts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return prompts


def sort_prompts(field: str = 'date', order: str = 'DESC') -> List[Dict]:
    """
    Сортировка промптов.
    
    Args:
        field: Поле для сортировки ('date', 'prompt', 'tags')
        order: Порядок сортировки ('ASC' или 'DESC')
    
    Returns:
        Отсортированный список промптов
    """
    valid_fields = ['date', 'prompt', 'tags']
    if field not in valid_fields:
        field = 'date'
    if order not in ['ASC', 'DESC']:
        order = 'DESC'
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM prompts ORDER BY {field} {order}")
    prompts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return prompts


# ==================== CRUD операции для таблицы models ====================

def create_model(name: str, api_url: str, api_id: str, is_active: int = 1) -> int:
    """
    Создать новую модель.
    
    Args:
        name: Название модели
        api_url: URL API
        api_id: Идентификатор переменной окружения с API-ключом
        is_active: Флаг активности (1 или 0)
    
    Returns:
        ID созданной модели
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO models (name, api_url, api_id, is_active) VALUES (?, ?, ?, ?)",
        (name, api_url, api_id, is_active)
    )
    model_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return model_id


def get_all_models() -> List[Dict]:
    """Получить все модели."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM models ORDER BY name")
    models = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return models


def get_active_models() -> List[Dict]:
    """Получить только активные модели."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM models WHERE is_active = 1 ORDER BY name")
    models = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return models


def update_model(model_id: int, name: str, api_url: str, api_id: str, is_active: int) -> bool:
    """
    Обновить модель.
    
    Args:
        model_id: ID модели
        name: Новое название
        api_url: Новый URL API
        api_id: Новый идентификатор API-ключа
        is_active: Флаг активности
    
    Returns:
        True если обновление успешно, False иначе
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE models SET name = ?, api_url = ?, api_id = ?, is_active = ? WHERE id = ?",
        (name, api_url, api_id, is_active, model_id)
    )
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def delete_model(model_id: int) -> bool:
    """
    Удалить модель.
    
    Args:
        model_id: ID модели
    
    Returns:
        True если удаление успешно, False иначе
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM models WHERE id = ?", (model_id,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def toggle_model_active(model_id: int, is_active: int) -> bool:
    """
    Переключить активность модели.
    
    Args:
        model_id: ID модели
        is_active: Новое значение активности (1 или 0)
    
    Returns:
        True если обновление успешно, False иначе
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE models SET is_active = ? WHERE id = ?", (is_active, model_id))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def search_models(query: str) -> List[Dict]:
    """
    Поиск моделей по названию или API URL.
    
    Args:
        query: Поисковый запрос
    
    Returns:
        Список найденных моделей
    """
    conn = get_connection()
    cursor = conn.cursor()
    search_term = f"%{query}%"
    cursor.execute(
        "SELECT * FROM models WHERE name LIKE ? OR api_url LIKE ? ORDER BY name",
        (search_term, search_term)
    )
    models = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return models


# ==================== CRUD операции для таблицы results ====================

def save_result(prompt_id: int, model_name: str, response_text: str) -> int:
    """
    Сохранить результат ответа модели.
    
    Args:
        prompt_id: ID промпта
        model_name: Название модели
        response_text: Текст ответа
    
    Returns:
        ID сохранённого результата
    """
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute(
        "INSERT INTO results (prompt_id, model_name, response_text, created_at) VALUES (?, ?, ?, ?)",
        (prompt_id, model_name, response_text, created_at)
    )
    result_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return result_id


def get_all_results() -> List[Dict]:
    """Получить все результаты."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM results ORDER BY created_at DESC")
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_results_by_prompt_id(prompt_id: int) -> List[Dict]:
    """
    Получить результаты по ID промпта.
    
    Args:
        prompt_id: ID промпта
    
    Returns:
        Список результатов для данного промпта
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM results WHERE prompt_id = ? ORDER BY created_at DESC",
        (prompt_id,)
    )
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def delete_result(result_id: int) -> bool:
    """
    Удалить результат.
    
    Args:
        result_id: ID результата
    
    Returns:
        True если удаление успешно, False иначе
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM results WHERE id = ?", (result_id,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def search_results(query: str) -> List[Dict]:
    """
    Поиск результатов по тексту ответа или названию модели.
    
    Args:
        query: Поисковый запрос
    
    Returns:
        Список найденных результатов
    """
    conn = get_connection()
    cursor = conn.cursor()
    search_term = f"%{query}%"
    cursor.execute(
        "SELECT * FROM results WHERE response_text LIKE ? OR model_name LIKE ? ORDER BY created_at DESC",
        (search_term, search_term)
    )
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def sort_results(field: str = 'created_at', order: str = 'DESC') -> List[Dict]:
    """
    Сортировка результатов.
    
    Args:
        field: Поле для сортировки ('created_at', 'model_name', 'prompt_id')
        order: Порядок сортировки ('ASC' или 'DESC')
    
    Returns:
        Отсортированный список результатов
    """
    valid_fields = ['created_at', 'model_name', 'prompt_id']
    if field not in valid_fields:
        field = 'created_at'
    if order not in ['ASC', 'DESC']:
        order = 'DESC'
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM results ORDER BY {field} {order}")
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


# ==================== Операции для таблицы settings ====================

def get_setting(key: str) -> Optional[str]:
    """
    Получить настройку по ключу.
    
    Args:
        key: Ключ настройки
    
    Returns:
        Значение настройки или None
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else None


def set_setting(key: str, value: str) -> bool:
    """
    Сохранить настройку.
    
    Args:
        key: Ключ настройки
        value: Значение настройки
    
    Returns:
        True если сохранение успешно
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, value)
    )
    conn.commit()
    conn.close()
    return True


def get_all_settings() -> Dict[str, str]:
    """
    Получить все настройки.
    
    Returns:
        Словарь всех настроек (ключ -> значение)
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    settings = {row['key']: row['value'] for row in cursor.fetchall()}
    conn.close()
    return settings
