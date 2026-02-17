"""
Модуль для работы с настройками и переменными окружения.
"""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
# Сначала загружаем .env, затем .env.local (если есть) для переопределения
load_dotenv()  # Загружает .env
load_dotenv('.env.local')  # Переопределяет значения из .env.local, если файл существует


def get_api_key(api_id: str) -> str:
    """
    Получить API-ключ из переменных окружения.
    
    Args:
        api_id: Идентификатор переменной окружения (например, 'OPENAI_API_KEY')
    
    Returns:
        Значение API-ключа или пустая строка, если ключ не найден
    """
    return os.getenv(api_id, '')


def get_setting(key: str, default: str = '') -> str:
    """
    Получить настройку из переменных окружения.
    
    Args:
        key: Ключ настройки
        default: Значение по умолчанию
    
    Returns:
        Значение настройки или default
    """
    return os.getenv(key, default)


def get_database_path() -> str:
    """
    Получить путь к файлу базы данных.
    
    Returns:
        Путь к файлу БД (по умолчанию 'chatlist.db')
    """
    return os.getenv('DATABASE_PATH', 'chatlist.db')
