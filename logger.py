"""
Модуль для логирования запросов и действий приложения.
"""
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler


def setup_logger(log_level: str = "INFO", log_file: str = "chatlist.log") -> logging.Logger:
    """
    Настроить логгер для приложения.
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
        log_file: Имя файла лога
    
    Returns:
        Настроенный объект логгера
    """
    logger = logging.getLogger('ChatList')
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Удаляем существующие обработчики
    logger.handlers.clear()
    
    # Формат логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Обработчик для файла (с ротацией)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


def log_request(logger: logging.Logger, model_name: str, prompt: str, success: bool, response: str = "", error: str = ""):
    """
    Записать лог запроса к модели.
    
    Args:
        logger: Объект логгера
        model_name: Название модели
        prompt: Текст промпта
        success: Успешность запроса
        response: Текст ответа (если успешно)
        error: Текст ошибки (если неуспешно)
    """
    if success:
        logger.info(f"Запрос к модели '{model_name}' успешен. Промпт: {prompt[:100]}...")
        logger.debug(f"Ответ от '{model_name}': {response[:500]}...")
    else:
        logger.error(f"Ошибка запроса к модели '{model_name}': {error}. Промпт: {prompt[:100]}...")


def log_action(logger: logging.Logger, action: str, details: str = ""):
    """
    Записать лог действия пользователя.
    
    Args:
        logger: Объект логгера
        action: Описание действия
        details: Дополнительные детали
    """
    logger.info(f"Действие: {action}. {details}")


# Глобальный логгер (инициализируется при первом импорте)
_logger = None


def get_logger() -> logging.Logger:
    """
    Получить глобальный логгер.
    
    Returns:
        Объект логгера
    """
    global _logger
    if _logger is None:
        # Загружаем уровень логирования из настроек
        import db
        db.init_database()
        log_level = db.get_setting('log_level') or 'INFO'
        _logger = setup_logger(log_level)
    return _logger
