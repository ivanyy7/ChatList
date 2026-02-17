"""
Модуль для отправки HTTP-запросов к API нейросетей.
Поддержка разных типов моделей (OpenAI, DeepSeek, Groq и т.д.).
"""
import requests
import threading
from typing import Dict, List, Optional, Callable, Tuple
from models import Model
from config import get_api_key


# Таймаут по умолчанию (секунды)
DEFAULT_TIMEOUT = 30


def load_api_keys() -> Dict[str, str]:
    """
    Загрузить все API-ключи из переменных окружения.
    
    Returns:
        Словарь с API-ключами (api_id -> api_key)
    """
    # Это вспомогательная функция, основная загрузка происходит через get_api_key()
    return {}


def detect_api_type(api_url: str) -> str:
    """
    Определить тип API по URL.
    
    Args:
        api_url: URL API
    
    Returns:
        Тип API: 'openai', 'deepseek', 'groq' или 'generic'
    """
    url_lower = api_url.lower()
    if 'openai.com' in url_lower:
        return 'openai'
    elif 'deepseek.com' in url_lower:
        return 'deepseek'
    elif 'groq.com' in url_lower:
        return 'groq'
    else:
        return 'generic'


def send_request_to_openai(model: Model, prompt: str, api_key: str, timeout: int = DEFAULT_TIMEOUT) -> Tuple[bool, str]:
    """
    Отправить запрос к OpenAI API.
    
    Args:
        model: Объект Model
        prompt: Текст промпта
        api_key: API-ключ
        timeout: Таймаут запроса в секундах
    
    Returns:
        Кортеж (успешность, ответ или сообщение об ошибке)
    """
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # Определяем модель из URL или используем название
    model_name = model.name.lower().replace(' ', '-')
    if 'gpt-4' in model_name:
        model_id = 'gpt-4'
    elif 'gpt-3.5' in model_name:
        model_id = 'gpt-3.5-turbo'
    else:
        model_id = 'gpt-3.5-turbo'  # По умолчанию
    
    data = {
        'model': model_id,
        'messages': [
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.7
    }
    
    try:
        response = requests.post(
            model.api_url,
            headers=headers,
            json=data,
            timeout=timeout
        )
        response.raise_for_status()
        result = response.json()
        
        if 'choices' in result and len(result['choices']) > 0:
            return True, result['choices'][0]['message']['content']
        else:
            return False, "Неожиданный формат ответа от API"
    
    except requests.exceptions.Timeout:
        return False, f"Таймаут запроса ({timeout} сек)"
    except requests.exceptions.RequestException as e:
        return False, f"Ошибка сети: {str(e)}"
    except Exception as e:
        return False, f"Неожиданная ошибка: {str(e)}"


def send_request_to_deepseek(model: Model, prompt: str, api_key: str, timeout: int = DEFAULT_TIMEOUT) -> Tuple[bool, str]:
    """
    Отправить запрос к DeepSeek API.
    
    Args:
        model: Объект Model
        prompt: Текст промпта
        api_key: API-ключ
        timeout: Таймаут запроса в секундах
    
    Returns:
        Кортез (успешность, ответ или сообщение об ошибке)
    """
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': 'deepseek-chat',
        'messages': [
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.7
    }
    
    try:
        response = requests.post(
            model.api_url,
            headers=headers,
            json=data,
            timeout=timeout
        )
        response.raise_for_status()
        result = response.json()
        
        if 'choices' in result and len(result['choices']) > 0:
            return True, result['choices'][0]['message']['content']
        else:
            return False, "Неожиданный формат ответа от API"
    
    except requests.exceptions.Timeout:
        return False, f"Таймаут запроса ({timeout} сек)"
    except requests.exceptions.RequestException as e:
        return False, f"Ошибка сети: {str(e)}"
    except Exception as e:
        return False, f"Неожиданная ошибка: {str(e)}"


def send_request_to_groq(model: Model, prompt: str, api_key: str, timeout: int = DEFAULT_TIMEOUT) -> Tuple[bool, str]:
    """
    Отправить запрос к Groq API.
    
    Args:
        model: Объект Model
        prompt: Текст промпта
        api_key: API-ключ
        timeout: Таймаут запроса в секундах
    
    Returns:
        Кортеж (успешность, ответ или сообщение об ошибке)
    """
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # Определяем модель из названия
    model_name = model.name.lower()
    if 'llama' in model_name:
        model_id = 'llama3-8b-8192'
    elif 'mixtral' in model_name:
        model_id = 'mixtral-8x7b-32768'
    else:
        model_id = 'llama3-8b-8192'  # По умолчанию
    
    data = {
        'messages': [
            {'role': 'user', 'content': prompt}
        ],
        'model': model_id
    }
    
    try:
        response = requests.post(
            model.api_url,
            headers=headers,
            json=data,
            timeout=timeout
        )
        response.raise_for_status()
        result = response.json()
        
        if 'choices' in result and len(result['choices']) > 0:
            return True, result['choices'][0]['message']['content']
        else:
            return False, "Неожиданный формат ответа от API"
    
    except requests.exceptions.Timeout:
        return False, f"Таймаут запроса ({timeout} сек)"
    except requests.exceptions.RequestException as e:
        return False, f"Ошибка сети: {str(e)}"
    except Exception as e:
        return False, f"Неожиданная ошибка: {str(e)}"


def send_request_to_generic(model: Model, prompt: str, api_key: str, timeout: int = DEFAULT_TIMEOUT) -> Tuple[bool, str]:
    """
    Отправить запрос к универсальному API (общий формат).
    
    Args:
        model: Объект Model
        prompt: Текст промпта
        api_key: API-ключ
        timeout: Таймаут запроса в секундах
    
    Returns:
        Кортеж (успешность, ответ или сообщение об ошибке)
    """
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': model.name,
        'messages': [
            {'role': 'user', 'content': prompt}
        ]
    }
    
    try:
        response = requests.post(
            model.api_url,
            headers=headers,
            json=data,
            timeout=timeout
        )
        response.raise_for_status()
        result = response.json()
        
        # Попытка извлечь ответ из разных возможных форматов
        if 'choices' in result and len(result['choices']) > 0:
            choice = result['choices'][0]
            if 'message' in choice:
                return True, choice['message'].get('content', str(choice))
            return True, str(choice)
        elif 'content' in result:
            return True, result['content']
        elif 'text' in result:
            return True, result['text']
        else:
            return False, "Неожиданный формат ответа от API"
    
    except requests.exceptions.Timeout:
        return False, f"Таймаут запроса ({timeout} сек)"
    except requests.exceptions.RequestException as e:
        return False, f"Ошибка сети: {str(e)}"
    except Exception as e:
        return False, f"Неожиданная ошибка: {str(e)}"


def send_request_to_model(model: Model, prompt: str, timeout: int = DEFAULT_TIMEOUT) -> Tuple[bool, str]:
    """
    Универсальная функция отправки запроса к модели.
    Автоматически определяет тип API и использует соответствующий обработчик.
    
    Args:
        model: Объект Model
        prompt: Текст промпта
        timeout: Таймаут запроса в секундах
    
    Returns:
        Кортеж (успешность, ответ или сообщение об ошибке)
    """
    # Получаем API-ключ
    api_key = get_api_key(model.api_id)
    if not api_key:
        return False, f"API-ключ '{model.api_id}' не найден в переменных окружения"
    
    # Определяем тип API
    api_type = detect_api_type(model.api_url)
    
    # Выбираем соответствующий обработчик
    if api_type == 'openai':
        return send_request_to_openai(model, prompt, api_key, timeout)
    elif api_type == 'deepseek':
        return send_request_to_deepseek(model, prompt, api_key, timeout)
    elif api_type == 'groq':
        return send_request_to_groq(model, prompt, api_key, timeout)
    else:
        return send_request_to_generic(model, prompt, api_key, timeout)


def send_to_all_models(
    models: List[Model],
    prompt: str,
    callback: Optional[Callable[[Model, bool, str], None]] = None,
    timeout: int = DEFAULT_TIMEOUT
) -> List[Dict]:
    """
    Отправить запрос ко всем моделям параллельно.
    
    Args:
        models: Список моделей для запроса
        prompt: Текст промпта
        callback: Опциональная функция обратного вызова для каждого результата
                  Принимает (model, success, response)
        timeout: Таймаут запроса в секундах
    
    Returns:
        Список словарей с результатами:
        [{'model': Model, 'success': bool, 'response': str}, ...]
    """
    results = []
    threads = []
    lock = threading.Lock()
    
    def send_to_model(model: Model):
        """Внутренняя функция для отправки запроса в отдельном потоке."""
        success, response = send_request_to_model(model, prompt, timeout)
        
        with lock:
            result = {
                'model': model,
                'success': success,
                'response': response
            }
            results.append(result)
            
            if callback:
                callback(model, success, response)
    
    # Создаём потоки для каждой модели
    for model in models:
        thread = threading.Thread(target=send_to_model, args=(model,))
        thread.start()
        threads.append(thread)
    
    # Ждём завершения всех потоков
    for thread in threads:
        thread.join()
    
    return results
