"""
Модуль для работы с моделями нейросетей.
Логика работы с моделями.
"""
from typing import List, Optional, Tuple
from db import get_all_models, get_active_models


class Model:
    """
    Класс для представления модели нейросети.
    """
    
    def __init__(self, model_id: int, name: str, api_url: str, api_id: str, is_active: int):
        """
        Инициализация модели.
        
        Args:
            model_id: ID модели в БД
            name: Название модели
            api_url: URL API для отправки запросов
            api_id: Идентификатор переменной окружения с API-ключом
            is_active: Флаг активности (1 - активна, 0 - неактивна)
        """
        self.id = model_id
        self.name = name
        self.api_url = api_url
        self.api_id = api_id
        self.is_active = is_active
    
    def __repr__(self):
        return f"Model(id={self.id}, name='{self.name}', is_active={self.is_active})"
    
    def to_dict(self) -> dict:
        """
        Преобразовать модель в словарь.
        
        Returns:
            Словарь с данными модели
        """
        return {
            'id': self.id,
            'name': self.name,
            'api_url': self.api_url,
            'api_id': self.api_id,
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Model':
        """
        Создать объект Model из словаря.
        
        Args:
            data: Словарь с данными модели
        
        Returns:
            Объект Model
        """
        return cls(
            model_id=data['id'],
            name=data['name'],
            api_url=data['api_url'],
            api_id=data['api_id'],
            is_active=data['is_active']
        )


def load_models_from_db() -> List[Model]:
    """
    Загрузить все модели из базы данных.
    
    Returns:
        Список объектов Model
    """
    models_data = get_all_models()
    return [Model.from_dict(model_data) for model_data in models_data]


def get_active_models_list() -> List[Model]:
    """
    Получить список только активных моделей.
    
    Returns:
        Список активных объектов Model
    """
    active_models_data = get_active_models()
    return [Model.from_dict(model_data) for model_data in active_models_data]


def validate_model_config(model: Model) -> Tuple[bool, Optional[str]]:
    """
    Проверить конфигурацию модели.
    
    Args:
        model: Объект Model для проверки
    
    Returns:
        Кортеж (успешность проверки, сообщение об ошибке или None)
    """
    if not model.name or not model.name.strip():
        return False, "Название модели не может быть пустым"
    
    if not model.api_url or not model.api_url.strip():
        return False, "URL API не может быть пустым"
    
    if not model.api_id or not model.api_id.strip():
        return False, "Идентификатор API-ключа не может быть пустым"
    
    # Проверка формата URL (базовая)
    if not (model.api_url.startswith('http://') or model.api_url.startswith('https://')):
        return False, "URL API должен начинаться с http:// или https://"
    
    return True, None
