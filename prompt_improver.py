"""
Модуль для улучшения промптов с помощью AI.
Использует существующий OpenRouter-клиент для отправки запросов.
"""
import json
import re
from typing import Dict, List, Optional, Tuple
from models import Model
from network import send_request_to_model


# Системные промпты для улучшения
IMPROVE_PROMPT_TEMPLATE = """Ты - эксперт по написанию эффективных промптов для AI-моделей. 

Твоя задача - улучшить следующий промпт, сделав его более четким, структурированным и эффективным.

Исходный промпт:
{prompt}

Требования к улучшенному промпту:
1. Сохрани основную суть и цель промпта
2. Сделай его более конкретным и детальным
3. Добавь структуру, если это уместно
4. Улучши формулировки для лучшего понимания AI-моделью
5. Сохрани стиль и тон оригинала

Верни ТОЛЬКО улучшенный промпт, без дополнительных объяснений."""

ALTERNATIVES_PROMPT_TEMPLATE = """Ты - эксперт по написанию эффективных промптов для AI-моделей.

Твоя задача - создать 2-3 альтернативных варианта переформулировки следующего промпта. Каждый вариант должен сохранять основную суть, но использовать разные формулировки и подходы.

Исходный промпт:
{prompt}

Требования к альтернативным вариантам:
1. Каждый вариант должен сохранять основную цель промпта
2. Используй разные стили и подходы к формулировке
3. Варианты должны быть равноценными по эффективности
4. Сделай варианты разнообразными

Верни ответ в следующем формате (строго соблюдай формат):
ВАРИАНТ 1:
[первый вариант промпта]

ВАРИАНТ 2:
[второй вариант промпта]

ВАРИАНТ 3:
[третий вариант промпта]"""

ADAPT_PROMPT_TEMPLATE = """Ты - эксперт по адаптации промптов под разные типы задач.

Исходный промпт:
{prompt}

Тип задачи: {task_type}

Адаптируй промпт под указанный тип задачи:
- "код" - для задач программирования, добавь требования к структуре кода, комментариям, обработке ошибок
- "анализ" - для аналитических задач, добавь требования к структуре анализа, выводам, доказательствам
- "креатив" - для творческих задач, добавь требования к стилю, тону, креативности

Верни ТОЛЬКО адаптированный промпт, без дополнительных объяснений."""

COMBINED_PROMPT_TEMPLATE = """Ты - эксперт по написанию эффективных промптов для AI-моделей.

Твоя задача - улучшить следующий промпт и создать альтернативные варианты.

Исходный промпт:
{prompt}

Верни ответ в следующем JSON-формате (строго соблюдай формат):
{{
  "improved": "улучшенный промпт здесь",
  "alternatives": [
    "первый альтернативный вариант",
    "второй альтернативный вариант",
    "третий альтернативный вариант"
  ]
}}

Если не можешь вернуть JSON, используй следующий текстовый формат:
УЛУЧШЕННЫЙ:
[улучшенный промпт]

АЛЬТЕРНАТИВЫ:
1. [первый вариант]
2. [второй вариант]
3. [третий вариант]"""


def improve_prompt(prompt_text: str, model: Model, timeout: int = 30) -> Tuple[bool, str]:
    """
    Улучшить промпт с помощью AI-модели.
    
    Args:
        prompt_text: Исходный текст промпта
        model: Модель для улучшения
        timeout: Таймаут запроса в секундах
    
    Returns:
        Кортеж (успешность, улучшенный промпт или сообщение об ошибке)
    """
    if not prompt_text or not prompt_text.strip():
        return False, "Промпт не может быть пустым"
    
    # Формируем промпт для улучшения
    system_prompt = IMPROVE_PROMPT_TEMPLATE.format(prompt=prompt_text)
    
    # Отправляем запрос
    success, response = send_request_to_model(model, system_prompt, timeout)
    
    if not success:
        return False, response
    
    # Очищаем ответ от возможных артефактов
    improved = response.strip()
    
    # Убираем кавычки, если модель их добавила
    if improved.startswith('"') and improved.endswith('"'):
        improved = improved[1:-1]
    if improved.startswith("'") and improved.endswith("'"):
        improved = improved[1:-1]
    
    return True, improved


def generate_alternatives(prompt_text: str, model: Model, timeout: int = 30) -> Tuple[bool, List[str]]:
    """
    Сгенерировать альтернативные варианты промпта.
    
    Args:
        prompt_text: Исходный текст промпта
        model: Модель для генерации
        timeout: Таймаут запроса в секундах
    
    Returns:
        Кортеж (успешность, список альтернативных вариантов или сообщение об ошибке)
    """
    if not prompt_text or not prompt_text.strip():
        return False, "Промпт не может быть пустым"
    
    # Формируем промпт для генерации альтернатив
    system_prompt = ALTERNATIVES_PROMPT_TEMPLATE.format(prompt=prompt_text)
    
    # Отправляем запрос
    success, response = send_request_to_model(model, system_prompt, timeout)
    
    if not success:
        return False, response
    
    # Парсим ответ
    alternatives = parse_alternatives(response)
    
    if not alternatives:
        return False, "Не удалось извлечь альтернативные варианты из ответа модели"
    
    return True, alternatives


def adapt_for_model_type(prompt_text: str, task_type: str, model: Model, timeout: int = 30) -> Tuple[bool, str]:
    """
    Адаптировать промпт под конкретный тип задачи.
    
    Args:
        prompt_text: Исходный текст промпта
        task_type: Тип задачи ('код', 'анализ', 'креатив')
        model: Модель для адаптации
        timeout: Таймаут запроса в секундах
    
    Returns:
        Кортеж (успешность, адаптированный промпт или сообщение об ошибке)
    """
    if not prompt_text or not prompt_text.strip():
        return False, "Промпт не может быть пустым"
    
    valid_types = ['код', 'анализ', 'креатив']
    if task_type not in valid_types:
        return False, f"Неверный тип задачи. Допустимые: {', '.join(valid_types)}"
    
    # Формируем промпт для адаптации
    system_prompt = ADAPT_PROMPT_TEMPLATE.format(prompt=prompt_text, task_type=task_type)
    
    # Отправляем запрос
    success, response = send_request_to_model(model, system_prompt, timeout)
    
    if not success:
        return False, response
    
    # Очищаем ответ
    adapted = response.strip()
    
    # Убираем кавычки, если модель их добавила
    if adapted.startswith('"') and adapted.endswith('"'):
        adapted = adapted[1:-1]
    if adapted.startswith("'") and adapted.endswith("'"):
        adapted = adapted[1:-1]
    
    return True, adapted


def improve_prompt_with_alternatives(prompt_text: str, model: Model, timeout: int = 30) -> Tuple[bool, Dict]:
    """
    Улучшить промпт и получить альтернативные варианты за один запрос.
    
    Args:
        prompt_text: Исходный текст промпта
        model: Модель для улучшения
        timeout: Таймаут запроса в секундах
    
    Returns:
        Кортеж (успешность, словарь с результатами или сообщение об ошибке):
        {
            'improved': str,
            'alternatives': List[str]
        }
    """
    if not prompt_text or not prompt_text.strip():
        return False, "Промпт не может быть пустым"
    
    # Формируем комбинированный промпт
    system_prompt = COMBINED_PROMPT_TEMPLATE.format(prompt=prompt_text)
    
    # Отправляем запрос
    success, response = send_request_to_model(model, system_prompt, timeout)
    
    if not success:
        return False, response
    
    # Пытаемся распарсить JSON
    result = parse_combined_response(response)
    
    if result:
        return True, result
    
    # Если JSON не получился, пытаемся распарсить текстовый формат
    result = parse_text_response(response)
    
    if result:
        return True, result
    
    return False, "Не удалось распарсить ответ модели"


def parse_alternatives(response: str) -> List[str]:
    """
    Распарсить альтернативные варианты из ответа модели.
    
    Args:
        response: Ответ модели
    
    Returns:
        Список альтернативных вариантов
    """
    alternatives = []
    
    # Пытаемся найти варианты по паттерну "ВАРИАНТ N:"
    pattern = r'ВАРИАНТ\s+\d+:\s*(.+?)(?=ВАРИАНТ\s+\d+:|$)'
    matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
    
    if matches:
        alternatives = [match.strip() for match in matches]
    else:
        # Пытаемся найти пронумерованный список
        pattern = r'\d+[\.\)]\s*(.+?)(?=\d+[\.\)]|$)'
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            alternatives = [match.strip() for match in matches[:3]]
        else:
            # Разделяем по строкам и берем непустые
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            # Берем первые 3 непустые строки как варианты
            alternatives = lines[:3]
    
    # Очищаем варианты от артефактов
    cleaned = []
    for alt in alternatives:
        alt = alt.strip()
        # Убираем кавычки
        if alt.startswith('"') and alt.endswith('"'):
            alt = alt[1:-1]
        if alt.startswith("'") and alt.endswith("'"):
            alt = alt[1:-1]
        # Убираем маркеры типа "ВАРИАНТ 1:" если остались
        alt = re.sub(r'^ВАРИАНТ\s+\d+:\s*', '', alt, flags=re.IGNORECASE)
        alt = re.sub(r'^\d+[\.\)]\s*', '', alt)
        if alt:
            cleaned.append(alt)
    
    return cleaned[:3]  # Возвращаем максимум 3 варианта


def parse_combined_response(response: str) -> Optional[Dict]:
    """
    Распарсить комбинированный ответ (JSON формат).
    
    Args:
        response: Ответ модели
    
    Returns:
        Словарь с результатами или None
    """
    # Пытаемся найти JSON в ответе
    json_match = re.search(r'\{[^{}]*"improved"[^{}]*"alternatives"[^{}]*\}', response, re.DOTALL)
    if json_match:
        try:
            result = json.loads(json_match.group())
            if 'improved' in result and 'alternatives' in result:
                return {
                    'improved': result['improved'],
                    'alternatives': result['alternatives'][:3]  # Максимум 3 варианта
                }
        except json.JSONDecodeError:
            pass
    
    # Пытаемся распарсить весь ответ как JSON
    try:
        result = json.loads(response)
        if 'improved' in result and 'alternatives' in result:
            return {
                'improved': result['improved'],
                'alternatives': result['alternatives'][:3]
            }
    except json.JSONDecodeError:
        pass
    
    return None


def parse_text_response(response: str) -> Optional[Dict]:
    """
    Распарсить текстовый ответ с улучшенным промптом и альтернативами.
    
    Args:
        response: Ответ модели
    
    Returns:
        Словарь с результатами или None
    """
    result = {'improved': '', 'alternatives': []}
    
    # Ищем улучшенный промпт
    improved_match = re.search(r'УЛУЧШЕННЫЙ:\s*(.+?)(?=АЛЬТЕРНАТИВЫ:|$)', response, re.DOTALL | re.IGNORECASE)
    if improved_match:
        result['improved'] = improved_match.group(1).strip()
    
    # Ищем альтернативы
    alternatives_match = re.search(r'АЛЬТЕРНАТИВЫ:\s*(.+?)$', response, re.DOTALL | re.IGNORECASE)
    if alternatives_match:
        alternatives_text = alternatives_match.group(1)
        alternatives = parse_alternatives(alternatives_text)
        result['alternatives'] = alternatives
    
    # Если не нашли структурированный формат, пытаемся извлечь по-другому
    if not result['improved']:
        # Берем первую часть как улучшенный промпт
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        if lines:
            result['improved'] = lines[0]
            result['alternatives'] = lines[1:4] if len(lines) > 1 else []
    
    if result['improved']:
        return result
    
    return None
