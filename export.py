"""
Модуль для экспорта результатов в различные форматы.
"""
import json
from datetime import datetime
from typing import List, Dict


def export_to_markdown(results: List[Dict], prompt_text: str = "", output_file: str = "results.md") -> bool:
    """
    Экспортировать результаты в Markdown формат.
    
    Args:
        results: Список результатов для экспорта
        prompt_text: Текст промпта (опционально)
        output_file: Путь к выходному файлу
    
    Returns:
        True если экспорт успешен, False иначе
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # Заголовок
            f.write("# Результаты сравнения моделей\n\n")
            f.write(f"**Дата экспорта:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            if prompt_text:
                f.write(f"## Промпт\n\n{prompt_text}\n\n")
            
            f.write("---\n\n")
            
            # Результаты по моделям
            for idx, result in enumerate(results, 1):
                model_name = result.get('model_name', 'Неизвестная модель')
                response_text = result.get('response_text', '')
                success = result.get('success', False)
                
                f.write(f"## {idx}. {model_name}\n\n")
                
                if not success:
                    f.write(f"**Статус:** ❌ Ошибка\n\n")
                    f.write(f"**Сообщение:** {response_text}\n\n")
                else:
                    f.write(f"**Статус:** ✅ Успешно\n\n")
                    f.write(f"**Ответ:**\n\n{response_text}\n\n")
                
                f.write("---\n\n")
        
        return True
    except Exception as e:
        print(f"Ошибка при экспорте в Markdown: {e}")
        return False


def export_to_json(results: List[Dict], prompt_text: str = "", output_file: str = "results.json") -> bool:
    """
    Экспортировать результаты в JSON формат.
    
    Args:
        results: Список результатов для экспорта
        prompt_text: Текст промпта (опционально)
        output_file: Путь к выходному файлу
    
    Returns:
        True если экспорт успешен, False иначе
    """
    try:
        export_data = {
            'export_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'prompt': prompt_text,
            'results': []
        }
        
        for result in results:
            export_data['results'].append({
                'model_name': result.get('model_name', 'Неизвестная модель'),
                'response_text': result.get('response_text', ''),
                'success': result.get('success', False),
                'selected': result.get('selected', False)
            })
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"Ошибка при экспорте в JSON: {e}")
        return False
