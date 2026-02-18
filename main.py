"""
Главный файл приложения ChatList.
Графический интерфейс на PyQt5.
"""
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional

# Отключаем системные звуки Windows для этого приложения
os.environ['QT_AUDIO_DEVICE'] = 'none'
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QCheckBox, QLineEdit, QMessageBox, QDialog, QDialogButtonBox,
    QHeaderView, QMenuBar, QMenu, QAction, QActionGroup, QStatusBar, QProgressBar, QFileDialog,
    QTextBrowser, QSizePolicy, QSpinBox, QGroupBox, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QCoreApplication, QTimer, QRectF
from PyQt5.QtGui import QFont, QPalette, QColor, QPainter, QLinearGradient, QBrush, QIcon

import db
import markdown
from models import Model, load_models_from_db, get_active_models_list
from network import send_to_all_models
from export import export_to_markdown, export_to_json
from logger import get_logger, log_request, log_action
from prompt_improver import improve_prompt_with_alternatives
from version import __version__


# Ключ настройки темы в БД
THEME_SETTING_KEY = 'theme'
THEME_LIGHT = 'light'
THEME_DARK = 'dark'
THEME_SYSTEM = 'system'


def _set_windows_dark_title_bar(app: QApplication, dark: bool) -> None:
    """
    Включить или отключить тёмную строку заголовка для окон в Windows 10/11.
    """
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        from ctypes import wintypes
        HWND = wintypes.HWND
        DWM_WA_USE_IMMERSIVE_DARK_MODE = 20  # Windows 10 1809+
        dwm = ctypes.windll.dwmapi
        for w in app.topLevelWidgets():
            if w.isWindow() and w.winId():
                hwnd = int(w.winId())
                value = ctypes.c_int(1 if dark else 0)
                dwm.DwmSetWindowAttribute(HWND(hwnd), DWM_WA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value))
    except Exception:
        pass


def apply_theme(app: QApplication, theme: str) -> None:
    """
    Применить тему к приложению.
    
    Args:
        app: Экземпляр QApplication
        theme: Одна из констант THEME_LIGHT, THEME_DARK, THEME_SYSTEM
    """
    if theme not in (THEME_LIGHT, THEME_DARK, THEME_SYSTEM):
        theme = THEME_SYSTEM
    
    app.setStyle('Fusion')
    
    if theme == THEME_DARK:
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        app.setPalette(palette)
        app.setStyleSheet("""
            QToolTip { color: #ffffff; background-color: #2a2a2a; border: 1px solid #3d3d3d; }
            QMenu::item:selected { background-color: #2a82da; }
        """)
        _set_windows_dark_title_bar(app, dark=True)
    elif theme == THEME_LIGHT:
        app.setPalette(app.style().standardPalette())
        app.setStyleSheet("")
        _set_windows_dark_title_bar(app, dark=False)
    else:
        # Системная тема — сбрасываем палитру и стили
        app.setPalette(app.style().standardPalette())
        app.setStyleSheet("")
        _set_windows_dark_title_bar(app, dark=False)


# Инструкция для автоматического добавления к промптам
MARKDOWN_FORMATTING_INSTRUCTION = (
    "\n\n"
    "**Важно:** Ответь в формате Markdown с использованием заголовков (# или ##), "
    "при необходимости подзаголовков (###), маркированных (-) или нумерованных (1.) списков. "
    "Используй форматирование для лучшей читаемости ответа."
)


def strip_markdown(text: str) -> str:
    """
    Удалить Markdown-разметку из текста, оставив только обычный текст.
    Используется для отображения в таблице результатов.
    """
    if not text:
        return text
    
    import re
    
    # Удаляем заголовки (# ## ###)
    text = re.sub(r'^#{1,6}\s+(.+)$', r'\1', text, flags=re.MULTILINE)
    
    # Удаляем маркированные списки (- * +)
    text = re.sub(r'^[\s]*[-*+]\s+', '', text, flags=re.MULTILINE)
    
    # Удаляем нумерованные списки (1. 2. и т.д.)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # Удаляем жирный текст (**текст** или __текст__)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    
    # Удаляем курсив (*текст* или _текст_)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', text)
    text = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'\1', text)
    
    # Удаляем код (`код`)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # Удаляем ссылки [текст](url) -> текст
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    # Удаляем изображения ![alt](url)
    text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', text)
    
    # Удаляем горизонтальные линии (--- или ***)
    text = re.sub(r'^[-*]{3,}$', '', text, flags=re.MULTILINE)
    
    # Удаляем блоки кода (```код```)
    text = re.sub(r'```[\s\S]*?```', '', text)
    
    # Удаляем цитаты (> текст)
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
    
    # Убираем лишние пустые строки (более 2 подряд)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Убираем пробелы в начале и конце строк
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    return text.strip()


class RequestThread(QThread):
    """Поток для выполнения запросов к моделям."""
    
    finished = pyqtSignal(list)  # Сигнал с результатами
    
    def __init__(self, models: List[Model], prompt: str):
        super().__init__()
        self.models = models
        self.prompt = prompt
    
    def run(self):
        """Выполнить запросы к моделям."""
        results = []
        for model in self.models:
            from network import send_request_to_model
            success, response = send_request_to_model(model, self.prompt)
            results.append({
                'model': model,
                'success': success,
                'response': response
            })
        self.finished.emit(results)


class ModelDialog(QDialog):
    """Диалог для добавления/редактирования модели."""
    
    def __init__(self, parent=None, model_data: Optional[Dict] = None):
        super().__init__(parent)
        self.model_data = model_data
        self.setWindowTitle("Добавить модель" if not model_data else "Редактировать модель")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Название модели
        layout.addWidget(QLabel("Название модели:"))
        self.name_edit = QLineEdit()
        if model_data:
            self.name_edit.setText(model_data.get('name', ''))
        layout.addWidget(self.name_edit)
        
        # URL API
        layout.addWidget(QLabel("URL API:"))
        self.api_url_edit = QLineEdit()
        if model_data:
            self.api_url_edit.setText(model_data.get('api_url', ''))
        layout.addWidget(self.api_url_edit)
        
        # Идентификатор API-ключа
        layout.addWidget(QLabel("Идентификатор API-ключа (имя переменной окружения):"))
        self.api_id_edit = QLineEdit()
        if model_data:
            self.api_id_edit.setText(model_data.get('api_id', ''))
        layout.addWidget(self.api_id_edit)
        
        # Активность
        self.active_checkbox = QCheckBox("Активна")
        if model_data:
            self.active_checkbox.setChecked(model_data.get('is_active', 1) == 1)
        else:
            self.active_checkbox.setChecked(True)
        layout.addWidget(self.active_checkbox)
        
        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def get_data(self) -> Dict:
        """Получить данные модели из формы."""
        return {
            'name': self.name_edit.text().strip(),
            'api_url': self.api_url_edit.text().strip(),
            'api_id': self.api_id_edit.text().strip(),
            'is_active': 1 if self.active_checkbox.isChecked() else 0
        }


class PromptsDialog(QDialog):
    """Диалог для просмотра и выбора промптов."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("История промптов")
        self.setMinimumSize(800, 600)
        self.selected_prompt_id = None
        
        layout = QVBoxLayout()
        
        # Поиск
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Поиск:"))
        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self.search_prompts)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)
        
        # Таблица промптов
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Дата", "Промпт", "Теги"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.doubleClicked.connect(self.accept_selection)
        layout.addWidget(self.table)
        
        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_selection)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        self.load_prompts()
    
    def load_prompts(self):
        """Загрузить промпты в таблицу."""
        prompts = db.get_all_prompts()
        self.table.setRowCount(len(prompts))
        
        for row, prompt in enumerate(prompts):
            self.table.setItem(row, 0, QTableWidgetItem(str(prompt['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(prompt['date']))
            self.table.setItem(row, 2, QTableWidgetItem(prompt['prompt']))
            self.table.setItem(row, 3, QTableWidgetItem(prompt['tags'] or ''))
        
        self.table.resizeColumnsToContents()
    
    def search_prompts(self):
        """Поиск промптов."""
        query = self.search_edit.text()
        if query:
            prompts = db.search_prompts(query)
        else:
            prompts = db.get_all_prompts()
        
        self.table.setRowCount(len(prompts))
        for row, prompt in enumerate(prompts):
            self.table.setItem(row, 0, QTableWidgetItem(str(prompt['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(prompt['date']))
            self.table.setItem(row, 2, QTableWidgetItem(prompt['prompt']))
            self.table.setItem(row, 3, QTableWidgetItem(prompt['tags'] or ''))
    
    def accept_selection(self):
        """Принять выбранный промпт."""
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.selected_prompt_id = int(self.table.item(current_row, 0).text())
            self.accept()


class PromptImproverDialog(QDialog):
    """Диалог для улучшения промптов с помощью AI."""
    
    def __init__(self, parent=None, prompt_text: str = "", models: List[Model] = None):
        super().__init__(parent)
        self.setWindowTitle("Улучшить промт")
        self.setMinimumSize(700, 600)
        self.selected_text = None
        self.models = models or []
        
        layout = QVBoxLayout()
        
        # Выбор модели для улучшения
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Модель для улучшения:"))
        self.model_combo = QComboBox()
        for model in self.models:
            self.model_combo.addItem(model.name, model)
        if self.model_combo.count() > 0:
            self.model_combo.setCurrentIndex(0)
        model_layout.addWidget(self.model_combo)
        layout.addLayout(model_layout)
        
        # Исходный промпт
        layout.addWidget(QLabel("Исходный промпт:"))
        self.original_edit = QTextEdit()
        self.original_edit.setReadOnly(True)
        self.original_edit.setPlainText(prompt_text)
        self.original_edit.setMaximumHeight(100)
        layout.addWidget(self.original_edit)
        
        # Улучшенный промпт
        layout.addWidget(QLabel("Улучшенный промпт:"))
        self.improved_edit = QTextEdit()
        self.improved_edit.setReadOnly(True)
        self.improved_edit.setPlaceholderText("Здесь появится улучшенный промпт...")
        self.improved_edit.setMaximumHeight(150)
        layout.addWidget(self.improved_edit)
        
        # Кнопка подстановки улучшенного
        self.insert_improved_button = QPushButton("📝 Подставить улучшенный")
        self.insert_improved_button.clicked.connect(lambda: self.insert_text(self.improved_edit.toPlainText()))
        self.insert_improved_button.setEnabled(False)
        layout.addWidget(self.insert_improved_button)
        
        # Альтернативные варианты
        layout.addWidget(QLabel("Альтернативные варианты:"))
        self.alternatives_widget = QWidget()
        alternatives_layout = QVBoxLayout()
        self.alternatives_widget.setLayout(alternatives_layout)
        
        self.alternative_edits = []
        self.insert_buttons = []
        
        for i in range(3):
            alt_layout = QHBoxLayout()
            alt_edit = QTextEdit()
            alt_edit.setReadOnly(True)
            alt_edit.setPlaceholderText(f"Вариант {i+1} появится здесь...")
            alt_edit.setMaximumHeight(80)
            self.alternative_edits.append(alt_edit)
            alt_layout.addWidget(alt_edit)
            
            insert_btn = QPushButton(f"📝 Вариант {i+1}")
            # Используем замыкание для правильной передачи индекса
            def make_insert_handler(index):
                return lambda: self.insert_text(self.alternative_edits[index].toPlainText())
            insert_btn.clicked.connect(make_insert_handler(i))
            insert_btn.setEnabled(False)
            self.insert_buttons.append(insert_btn)
            alt_layout.addWidget(insert_btn)
            
            alternatives_layout.addLayout(alt_layout)
        
        layout.addWidget(self.alternatives_widget)
        
        # Индикатор загрузки
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Неопределенный прогресс
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        self.improve_button = QPushButton("✨ Улучшить")
        self.improve_button.clicked.connect(self.improve_prompt)
        buttons_layout.addWidget(self.improve_button)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons_layout.addWidget(buttons)
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def improve_prompt(self):
        """Улучшить промпт с помощью выбранной модели."""
        prompt_text = self.original_edit.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "Ошибка", "Исходный промпт не может быть пустым")
            return
        
        if self.model_combo.count() == 0:
            QMessageBox.warning(self, "Ошибка", "Нет доступных моделей для улучшения")
            return
        
        model = self.model_combo.currentData()
        if not model:
            QMessageBox.warning(self, "Ошибка", "Выберите модель для улучшения")
            return
        
        # Блокируем кнопки и показываем индикатор
        self.improve_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.insert_improved_button.setEnabled(False)
        for btn in self.insert_buttons:
            btn.setEnabled(False)
        
        # Очищаем предыдущие результаты
        self.improved_edit.clear()
        for edit in self.alternative_edits:
            edit.clear()
        
        # Выполняем улучшение в отдельном потоке
        self.improve_thread = ImprovePromptThread(prompt_text, model)
        self.improve_thread.finished.connect(self.on_improvement_finished)
        self.improve_thread.start()
    
    def on_improvement_finished(self):
        """Обработчик завершения улучшения промпта."""
        self.progress_bar.setVisible(False)
        self.improve_button.setEnabled(True)
        
        success = self.improve_thread.success
        result = self.improve_thread.result
        
        if not success:
            QMessageBox.critical(self, "Ошибка", f"Не удалось улучшить промпт:\n{result}")
            return
        
        # Отображаем результаты
        if isinstance(result, dict):
            improved = result.get('improved', '')
            alternatives = result.get('alternatives', [])
            
            if improved:
                self.improved_edit.setPlainText(improved)
                self.insert_improved_button.setEnabled(True)
            
            for i, alt in enumerate(alternatives[:3]):
                if i < len(self.alternative_edits):
                    self.alternative_edits[i].setPlainText(alt)
                    self.insert_buttons[i].setEnabled(True)
        else:
            QMessageBox.warning(self, "Предупреждение", "Неожиданный формат ответа")
    
    def insert_text(self, text: str):
        """Подставить текст в поле ввода промпта в главном окне."""
        if text and text.strip():
            self.selected_text = text.strip()
            self.accept()


class ImprovePromptThread(QThread):
    """Поток для улучшения промпта в фоновом режиме."""
    
    finished = pyqtSignal()
    
    def __init__(self, prompt_text: str, model: Model):
        super().__init__()
        self.prompt_text = prompt_text
        self.model = model
        self.success = False
        self.result = None
    
    def run(self):
        """Выполнить улучшение промпта."""
        self.success, self.result = improve_prompt_with_alternatives(
            self.prompt_text,
            self.model,
            timeout=30
        )
        self.finished.emit()


class ModelsDialog(QDialog):
    """Диалог для управления моделями."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление моделями")
        self.setMinimumSize(900, 600)
        
        layout = QVBoxLayout()
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        self.add_button = QPushButton("Добавить")
        self.add_button.clicked.connect(self.add_model)
        self.edit_button = QPushButton("Редактировать")
        self.edit_button.clicked.connect(self.edit_model)
        self.delete_button = QPushButton("Удалить")
        self.delete_button.clicked.connect(self.delete_model)
        self.toggle_button = QPushButton("Переключить активность")
        self.toggle_button.clicked.connect(self.toggle_active)
        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.edit_button)
        buttons_layout.addWidget(self.delete_button)
        buttons_layout.addWidget(self.toggle_button)
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Таблица моделей
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Название", "URL API", "API ID", "Активна"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)
        
        # Кнопка закрытия
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
        
        self.setLayout(layout)
        self.load_models()
    
    def load_models(self):
        """Загрузить модели в таблицу."""
        models = db.get_all_models()
        self.table.setRowCount(len(models))
        
        for row, model in enumerate(models):
            self.table.setItem(row, 0, QTableWidgetItem(str(model['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(model['name']))
            self.table.setItem(row, 2, QTableWidgetItem(model['api_url']))
            self.table.setItem(row, 3, QTableWidgetItem(model['api_id']))
            self.table.setItem(row, 4, QTableWidgetItem("Да" if model['is_active'] else "Нет"))
        
        self.table.resizeColumnsToContents()
    
    def add_model(self):
        """Добавить новую модель."""
        dialog = ModelDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            # Валидация полей
            if not data['name'] or not data['name'].strip():
                QMessageBox.warning(self, "Ошибка", "Введите название модели")
                return
            if not data['api_url'] or not data['api_url'].strip():
                QMessageBox.warning(self, "Ошибка", "Введите URL API")
                return
            if not data['api_id'] or not data['api_id'].strip():
                QMessageBox.warning(self, "Ошибка", "Введите идентификатор API-ключа")
                return
            
            # Проверка формата URL
            if not (data['api_url'].startswith('http://') or data['api_url'].startswith('https://')):
                QMessageBox.warning(self, "Ошибка", "URL должен начинаться с http:// или https://")
                return
            
            try:
                db.create_model(data['name'], data['api_url'], data['api_id'], data['is_active'])
                self.load_models()
                log_action(get_logger(), "Добавлена модель", data['name'])
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось добавить модель: {str(e)}")
    
    def edit_model(self):
        """Редактировать выбранную модель."""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите модель для редактирования")
            return
        
        model_id = int(self.table.item(current_row, 0).text())
        model_data = db.get_all_models()
        model = next((m for m in model_data if m['id'] == model_id), None)
        
        if model:
            dialog = ModelDialog(self, model)
            if dialog.exec_() == QDialog.Accepted:
                data = dialog.get_data()
                # Валидация полей
                if not data['name'] or not data['name'].strip():
                    QMessageBox.warning(self, "Ошибка", "Введите название модели")
                    return
                if not data['api_url'] or not data['api_url'].strip():
                    QMessageBox.warning(self, "Ошибка", "Введите URL API")
                    return
                if not data['api_id'] or not data['api_id'].strip():
                    QMessageBox.warning(self, "Ошибка", "Введите идентификатор API-ключа")
                    return
                
                # Проверка формата URL
                if not (data['api_url'].startswith('http://') or data['api_url'].startswith('https://')):
                    QMessageBox.warning(self, "Ошибка", "URL должен начинаться с http:// или https://")
                    return
                
                try:
                    db.update_model(model_id, data['name'], data['api_url'], data['api_id'], data['is_active'])
                    self.load_models()
                    log_action(get_logger(), "Обновлена модель", data['name'])
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Не удалось обновить модель: {str(e)}")
    
    def delete_model(self):
        """Удалить выбранную модель."""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите модель для удаления")
            return
        
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены, что хотите удалить эту модель?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            model_id = int(self.table.item(current_row, 0).text())
            db.delete_model(model_id)
            self.load_models()
    
    def toggle_active(self):
        """Переключить активность выбранной модели."""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите модель")
            return
        
        model_id = int(self.table.item(current_row, 0).text())
        current_status = self.table.item(current_row, 4).text()
        new_status = 0 if current_status == "Да" else 1
        db.toggle_model_active(model_id, new_status)
        self.load_models()


class ResultsDialog(QDialog):
    """Диалог для просмотра сохранённых результатов."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Сохранённые результаты")
        self.setMinimumSize(900, 600)
        self.resize(1000, 700)
        
        # Проверяем текущую тему
        current_theme = db.get_setting(THEME_SETTING_KEY) or THEME_SYSTEM
        is_dark = current_theme == THEME_DARK
        
        # Применяем тёмную тему к диалогу, если выбрана тёмная тема
        if is_dark:
            self.setStyleSheet("""
                QDialog {
                    background-color: #353535;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                }
                QLineEdit {
                    background-color: #2a2a2a;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 4px;
                    border-radius: 3px;
                }
                QTableWidget {
                    background-color: #2a2a2a;
                    color: #ffffff;
                    gridline-color: #555555;
                    selection-background-color: #2a82da;
                }
                QHeaderView::section {
                    background-color: #353535;
                    color: #ffffff;
                    padding: 4px;
                    border: 1px solid #555555;
                }
                QPushButton {
                    background-color: #353535;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 6px 20px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #2a82da;
                    border-color: #2a82da;
                }
                QPushButton:pressed {
                    background-color: #1e5fa0;
                }
                QPushButton:disabled {
                    background-color: #2a2a2a;
                    color: #888888;
                    border-color: #444444;
                }
            """)
            # Тёмная полоса заголовка для Windows
            app = QApplication.instance()
            if app:
                _set_windows_dark_title_bar(app, dark=True)
        
        # Хранилище полных текстов результатов
        self.full_results: List[Dict] = []
        
        layout = QVBoxLayout()
        
        # Поиск
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Поиск:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Введите текст для поиска...")
        self.search_edit.textChanged.connect(self.search_results)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)
        
        # Таблица результатов
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Промпт ID", "Модель", "Ответ", "Дата"])
        
        # Настраиваем колонки
        self.table.setColumnWidth(0, 50)  # ID
        self.table.setColumnWidth(1, 80)  # Промпт ID
        self.table.setColumnWidth(2, 200)  # Модель
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)  # Ответ растягивается
        self.table.setColumnWidth(4, 150)  # Дата
        
        # Настраиваем отображение строк - компактное, без пропусков
        self.table.setWordWrap(False)  # Отключаем перенос текста для компактности
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)  # Фиксированная высота строк
        self.table.verticalHeader().setDefaultSectionSize(40)  # Компактная высота строк
        self.table.verticalHeader().setVisible(False)  # Скрываем номера строк для экономии места
        
        # Включаем выбор строк
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        
        # Подключаем двойной клик для открытия
        self.table.itemDoubleClicked.connect(self.open_selected_result)
        
        layout.addWidget(self.table)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        self.open_button = QPushButton("Открыть")
        self.open_button.clicked.connect(self.open_selected_result)
        self.open_button.setEnabled(False)
        self.open_button.setToolTip("Открыть выбранный результат в формате Markdown")
        buttons_layout.addWidget(self.open_button)
        
        buttons_layout.addStretch()
        
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.accept)
        buttons_layout.addWidget(close_button)
        
        layout.addLayout(buttons_layout)
        
        # Подключаем сигнал изменения выбора
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        
        self.setLayout(layout)
        self.load_results()
    
    def on_selection_changed(self):
        """Обработчик изменения выбора в таблице."""
        has_selection = len(self.table.selectedItems()) > 0
        self.open_button.setEnabled(has_selection)
    
    def load_results(self):
        """Загрузить результаты в таблицу."""
        self.full_results = db.get_all_results()
        self.update_table(self.full_results)
    
    def update_table(self, results: List[Dict]):
        """Обновить таблицу с результатами."""
        self.table.setRowCount(len(results))
        
        for row, result in enumerate(results):
            self.table.setItem(row, 0, QTableWidgetItem(str(result['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(str(result['prompt_id'])))
            self.table.setItem(row, 2, QTableWidgetItem(result['model_name']))
            
            # Показываем текст ответа (обрезаем для компактности, полный текст в tooltip)
            response_text = result['response_text'] or ""
            # Обрезаем до 100 символов для компактного отображения
            display_text = response_text[:100] + "..." if len(response_text) > 100 else response_text
            response_item = QTableWidgetItem(display_text)
            response_item.setToolTip(response_text)  # Полный текст в подсказке
            self.table.setItem(row, 3, response_item)
            
            self.table.setItem(row, 4, QTableWidgetItem(result['created_at']))
        
        # Устанавливаем фиксированную высоту для всех строк (компактное отображение)
        for row in range(self.table.rowCount()):
            self.table.setRowHeight(row, 40)
    
    def search_results(self):
        """Поиск результатов."""
        query = self.search_edit.text().strip().lower()
        if query:
            # Фильтруем результаты по запросу
            filtered_results = [
                r for r in self.full_results
                if query in str(r['id']).lower() or
                   query in str(r['prompt_id']).lower() or
                   query in r['model_name'].lower() or
                   query in (r['response_text'] or "").lower() or
                   query in (r['created_at'] or "").lower()
            ]
            self.update_table(filtered_results)
        else:
            self.update_table(self.full_results)
    
    def open_selected_result(self):
        """Открыть выбранный результат в формате Markdown."""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Предупреждение", "Выберите результат для просмотра")
            return
        
        row = selected_rows[0].row()
        if row < 0 or row >= self.table.rowCount():
            return
        
        # Получаем данные из таблицы напрямую
        id_item = self.table.item(row, 0)
        model_item = self.table.item(row, 2)
        response_item = self.table.item(row, 3)
        
        if not id_item or not model_item or not response_item:
            return
        
        # Получаем полный текст ответа из базы данных по ID
        result_id = int(id_item.text())
        result = next((r for r in self.full_results if r['id'] == result_id), None)
        
        if not result:
            # Если не нашли в полном списке, используем данные из таблицы
            response_text = response_item.text()
            model_name = model_item.text()
        else:
            response_text = result['response_text'] or ""
            model_name = result['model_name']
        
        # Открываем диалог просмотра Markdown
        dialog = MarkdownViewerDialog(
            self,
            title=f"Ответ от {model_name}",
            content=response_text
        )
        dialog.exec_()


def markdown_to_html(text: str) -> str:
    """Конвертировать Markdown в HTML с расширенной поддержкой форматирования."""
    if not text or not text.strip():
        return "<p class='empty'><em>(Пусто)</em></p>"
    html_body = markdown.markdown(
        text,
        extensions=['extra', 'nl2br', 'sane_lists'],
        output_format='html5'
    )
    # Если в ответе нет заголовков и списков — выделяем первую строку как заголовок
    if '<h1>' not in html_body and '<h2>' not in html_body and '<h3>' not in html_body:
        if html_body.strip().startswith('<p>'):
            first_p_end = html_body.find('</p>') + 4
            first_p = html_body[:first_p_end]
            rest = html_body[first_p_end:]
            first_p = first_p.replace('<p>', '<p class="lead">', 1)
            html_body = first_p + rest
    return html_body


# Профессиональные стили для отображения Markdown
MARKDOWN_VIEWER_CSS = """
* { box-sizing: border-box; }
body {
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 15px;
    line-height: 1.7;
    color: #1a1a1a;
    margin: 0;
    padding: 24px 28px;
    background: #fafafa;
    max-width: 900px;
}
.lead {
    font-size: 1.35em !important;
    font-weight: 600 !important;
    color: #0d47a1 !important;
    margin-bottom: 1em !important;
    line-height: 1.4 !important;
}
h1 {
    font-size: 2em;
    font-weight: 700;
    color: #0d47a1;
    margin: 0 0 0.5em 0;
    padding-bottom: 0.35em;
    border-bottom: 2px solid #1976d2;
    letter-spacing: -0.02em;
}
h2 {
    font-size: 1.5em;
    font-weight: 600;
    color: #1565c0;
    margin: 1.2em 0 0.45em 0;
    padding-bottom: 0.2em;
    border-bottom: 1px solid #bbdefb;
}
h3 {
    font-size: 1.25em;
    font-weight: 600;
    color: #1976d2;
    margin: 1em 0 0.35em 0;
}
h4, h5, h6 {
    font-size: 1.1em;
    font-weight: 600;
    color: #333;
    margin: 0.8em 0 0.3em 0;
}
p {
    margin: 0 0 0.75em 0;
    text-align: justify;
}
strong, b {
    font-weight: 700;
    color: #111;
}
em, i {
    font-style: italic;
    color: #424242;
}
code {
    background: #e3f2fd;
    color: #0d47a1;
    padding: 3px 8px;
    border-radius: 4px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 0.92em;
    border: 1px solid #bbdefb;
}
pre {
    background: #263238;
    color: #eceff1;
    padding: 16px 20px;
    border-radius: 8px;
    overflow-x: auto;
    margin: 1em 0;
    border-left: 4px solid #1976d2;
    font-size: 0.9em;
    line-height: 1.5;
}
pre code {
    background: none;
    color: inherit;
    padding: 0;
    border: none;
}
ul {
    margin: 0.6em 0;
    padding-left: 1.6em;
    list-style: none;
}
ul li {
    position: relative;
    margin: 0.35em 0;
    padding-left: 0.5em;
}
ul li::before {
    content: "\\2022";
    position: absolute;
    left: -1em;
    color: #1976d2;
    font-weight: bold;
    font-size: 1.2em;
}
ol {
    margin: 0.6em 0;
    padding-left: 2em;
    counter-reset: item;
}
ol li {
    margin: 0.35em 0;
    padding-left: 0.4em;
}
ol li::marker {
    color: #1976d2;
    font-weight: 600;
}
blockquote {
    border-left: 4px solid #1976d2;
    margin: 1em 0;
    padding: 12px 20px;
    background: #e3f2fd;
    color: #0d47a1;
    border-radius: 0 8px 8px 0;
    font-style: italic;
}
a {
    color: #1565c0;
    text-decoration: none;
    border-bottom: 1px solid #90caf9;
}
a:hover {
    color: #0d47a1;
    border-bottom-color: #1976d2;
}
hr {
    border: none;
    border-top: 2px solid #bbdefb;
    margin: 1.5em 0;
}
table {
    border-collapse: collapse;
    margin: 1em 0;
    width: 100%;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
th, td {
    border: 1px solid #e0e0e0;
    padding: 10px 14px;
    text-align: left;
}
th {
    background: #1976d2;
    color: #fff;
    font-weight: 600;
}
tr:nth-child(even) {
    background: #f5f5f5;
}
tr:hover {
    background: #e3f2fd;
}
"""

# Тёмная версия CSS для Markdown
MARKDOWN_VIEWER_CSS_DARK = """
* { box-sizing: border-box; }
body {
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 15px;
    line-height: 1.7;
    color: #e0e0e0;
    margin: 0;
    padding: 24px 28px;
    background: #2a2a2a;
    max-width: 900px;
}
.lead {
    font-size: 1.35em !important;
    font-weight: 600 !important;
    color: #64b5f6 !important;
    margin-bottom: 1em !important;
    line-height: 1.4 !important;
}
h1 {
    font-size: 2em;
    font-weight: 700;
    color: #64b5f6;
    margin: 0 0 0.5em 0;
    padding-bottom: 0.35em;
    border-bottom: 2px solid #42a5f5;
    letter-spacing: -0.02em;
}
h2 {
    font-size: 1.5em;
    font-weight: 600;
    color: #90caf9;
    margin: 1.2em 0 0.45em 0;
    padding-bottom: 0.2em;
    border-bottom: 1px solid #555555;
}
h3 {
    font-size: 1.25em;
    font-weight: 600;
    color: #90caf9;
    margin: 1em 0 0.35em 0;
}
h4, h5, h6 {
    font-size: 1.1em;
    font-weight: 600;
    color: #b0bec5;
    margin: 0.8em 0 0.3em 0;
}
p {
    margin: 0 0 0.75em 0;
    text-align: justify;
    color: #e0e0e0;
}
strong, b {
    font-weight: 700;
    color: #ffffff;
}
em, i {
    font-style: italic;
    color: #b0bec5;
}
code {
    background: #1e1e1e;
    color: #ce9178;
    padding: 3px 8px;
    border-radius: 4px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 0.92em;
    border: 1px solid #444444;
}
pre {
    background: #1e1e1e;
    color: #d4d4d4;
    padding: 16px 20px;
    border-radius: 8px;
    overflow-x: auto;
    margin: 1em 0;
    border-left: 4px solid #42a5f5;
    font-size: 0.9em;
    line-height: 1.5;
}
pre code {
    background: none;
    color: inherit;
    padding: 0;
    border: none;
}
ul {
    margin: 0.6em 0;
    padding-left: 1.6em;
    list-style: none;
}
ul li {
    position: relative;
    margin: 0.35em 0;
    padding-left: 0.5em;
    color: #e0e0e0;
}
ul li::before {
    content: "\\2022";
    position: absolute;
    left: -1em;
    color: #64b5f6;
    font-weight: bold;
    font-size: 1.2em;
}
ol {
    margin: 0.6em 0;
    padding-left: 2em;
    counter-reset: item;
}
ol li {
    margin: 0.35em 0;
    padding-left: 0.4em;
    color: #e0e0e0;
}
ol li::marker {
    color: #64b5f6;
    font-weight: 600;
}
blockquote {
    border-left: 4px solid #42a5f5;
    margin: 1em 0;
    padding: 12px 20px;
    background: #1e1e1e;
    color: #90caf9;
    border-radius: 0 8px 8px 0;
    font-style: italic;
}
a {
    color: #64b5f6;
    text-decoration: none;
    border-bottom: 1px solid #555555;
}
a:hover {
    color: #90caf9;
    border-bottom-color: #64b5f6;
}
hr {
    border: none;
    border-top: 2px solid #555555;
    margin: 1.5em 0;
}
table {
    border-collapse: collapse;
    margin: 1em 0;
    width: 100%;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}
th, td {
    border: 1px solid #444444;
    padding: 10px 14px;
    text-align: left;
}
th {
    background: #1976d2;
    color: #fff;
    font-weight: 600;
}
tr:nth-child(even) {
    background: #333333;
}
tr:hover {
    background: #3d3d3d;
}
"""


class MarkdownViewerDialog(QDialog):
    """Диалог для отображения ответа в форматированном Markdown."""
    
    def __init__(self, parent=None, title: str = "Ответ", content: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(720, 560)
        self.resize(800, 600)
        
        # Проверяем текущую тему
        current_theme = db.get_setting(THEME_SETTING_KEY) or THEME_SYSTEM
        is_dark = current_theme == THEME_DARK
        
        # Применяем тёмную тему к диалогу, если выбрана тёмная тема
        if is_dark:
            self.setStyleSheet("""
                QDialog {
                    background-color: #353535;
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #353535;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 6px 20px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #2a82da;
                    border-color: #2a82da;
                }
                QPushButton:pressed {
                    background-color: #1e5fa0;
                }
            """)
            # Тёмная полоса заголовка для Windows
            app = QApplication.instance()
            if app:
                _set_windows_dark_title_bar(app, dark=True)
        
        layout = QVBoxLayout()
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        
        # Выбираем CSS в зависимости от темы
        if is_dark:
            browser_bg = "#2a2a2a"
            css = MARKDOWN_VIEWER_CSS_DARK
        else:
            browser_bg = "#fafafa"
            css = MARKDOWN_VIEWER_CSS
        
        self.browser.setStyleSheet(f"QTextBrowser {{ background-color: {browser_bg}; }}")
        
        html_content = markdown_to_html(content if content else "")
        full_html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{html_content}</body></html>"
        self.browser.setHtml(full_html)
        
        layout.addWidget(self.browser)
        
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)


class SettingsDialog(QDialog):
    """Диалог настроек приложения."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setMinimumSize(500, 400)
        self.resize(550, 450)
        
        # Проверяем текущую тему
        current_theme = db.get_setting(THEME_SETTING_KEY) or THEME_SYSTEM
        is_dark = current_theme == THEME_DARK
        
        # Применяем тёмную тему к диалогу, если выбрана тёмная тема
        if is_dark:
            self.setStyleSheet("""
                QDialog {
                    background-color: #353535;
                    color: #ffffff;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #555555;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
                QRadioButton {
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                }
                QSpinBox {
                    background-color: #2a2a2a;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 4px;
                    border-radius: 3px;
                }
                QPushButton {
                    background-color: #353535;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 6px 20px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #2a82da;
                    border-color: #2a82da;
                }
                QPushButton:pressed {
                    background-color: #1e5fa0;
                }
            """)
            # Тёмная полоса заголовка для Windows
            app = QApplication.instance()
            if app:
                _set_windows_dark_title_bar(app, dark=True)
        
        layout = QVBoxLayout()
        
        # Группа "Тема"
        theme_group = QGroupBox("Тема оформления")
        theme_layout = QVBoxLayout()
        
        self.theme_button_group = QButtonGroup(self)
        
        self.theme_light_radio = QRadioButton("Светлая")
        self.theme_light_radio.setChecked(current_theme == THEME_LIGHT)
        self.theme_button_group.addButton(self.theme_light_radio, 0)
        theme_layout.addWidget(self.theme_light_radio)
        
        self.theme_dark_radio = QRadioButton("Тёмная")
        self.theme_dark_radio.setChecked(current_theme == THEME_DARK)
        self.theme_button_group.addButton(self.theme_dark_radio, 1)
        theme_layout.addWidget(self.theme_dark_radio)
        
        self.theme_system_radio = QRadioButton("Системная")
        self.theme_system_radio.setChecked(current_theme == THEME_SYSTEM)
        self.theme_button_group.addButton(self.theme_system_radio, 2)
        theme_layout.addWidget(self.theme_system_radio)
        
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # Группа "Размер шрифта"
        font_group = QGroupBox("Размер шрифта панелей")
        font_layout = QVBoxLayout()
        
        font_info_layout = QHBoxLayout()
        font_info_layout.addWidget(QLabel("Размер шрифта:"))
        
        # Получаем текущий размер шрифта из настроек
        font_size_str = db.get_setting('font_size') or '12'
        try:
            current_font_size = int(font_size_str)
        except ValueError:
            current_font_size = 12
        
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setMinimum(8)
        self.font_size_spinbox.setMaximum(24)
        self.font_size_spinbox.setValue(current_font_size)
        self.font_size_spinbox.setSuffix(" px")
        font_info_layout.addWidget(self.font_size_spinbox)
        font_info_layout.addStretch()
        
        font_layout.addLayout(font_info_layout)
        font_layout.addWidget(QLabel("Изменения вступят в силу после перезапуска приложения."))
        
        font_group.setLayout(font_layout)
        layout.addWidget(font_group)
        
        layout.addStretch()
        
        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def get_selected_theme(self):
        """Получить выбранную тему."""
        if self.theme_light_radio.isChecked():
            return THEME_LIGHT
        elif self.theme_dark_radio.isChecked():
            return THEME_DARK
        else:
            return THEME_SYSTEM
    
    def get_font_size(self):
        """Получить выбранный размер шрифта."""
        return self.font_size_spinbox.value()


class AboutDialog(QDialog):
    """Диалог 'О программе'."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("О программе")
        self.setMinimumSize(500, 400)
        self.resize(550, 450)
        
        # Проверяем текущую тему
        current_theme = db.get_setting(THEME_SETTING_KEY) or THEME_SYSTEM
        is_dark = current_theme == THEME_DARK
        
        # Применяем тёмную тему к диалогу, если выбрана тёмная тема
        if is_dark:
            self.setStyleSheet("""
                QDialog {
                    background-color: #353535;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #353535;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 6px 20px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #2a82da;
                    border-color: #2a82da;
                }
                QPushButton:pressed {
                    background-color: #1e5fa0;
                }
            """)
            # Тёмная полоса заголовка для Windows
            app = QApplication.instance()
            if app:
                _set_windows_dark_title_bar(app, dark=True)
        
        layout = QVBoxLayout()
        
        # Название программы
        title_label = QLabel("ChatList")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Версия
        version_label = QLabel(f"Версия {__version__}")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
        
        layout.addSpacing(20)
        
        # Описание
        description_text = """
        <p style="text-align: center;">
            <b>ChatList</b> — это Python-приложение для сравнения ответов различных нейросетей.
        </p>
        
        <p>
            Программа позволяет отправлять один и тот же промпт в несколько нейросетей 
            и сравнивать их ответы. Вы можете сохранять результаты в базу данных, 
            управлять моделями и промптами, а также использовать AI-ассистента для 
            улучшения ваших промптов.
        </p>
        
        <p><b>Основные возможности:</b></p>
        <ul>
            <li>Отправка промптов в несколько моделей одновременно</li>
            <li>Сравнение ответов в удобной таблице</li>
            <li>Сохранение результатов в базу данных</li>
            <li>Управление моделями и промптами</li>
            <li>AI-ассистент для улучшения промптов</li>
            <li>Экспорт результатов в Markdown и JSON</li>
            <li>Настройка темы оформления</li>
        </ul>
        
        <p><b>Технологии:</b></p>
        <ul>
            <li>Python 3.11+</li>
            <li>PyQt5</li>
            <li>SQLite</li>
            <li>OpenRouter API</li>
        </ul>
        """
        
        description_label = QLabel(description_text)
        description_label.setWordWrap(True)
        description_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        layout.addWidget(description_label)
        
        layout.addStretch()
        
        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)


class MovingSegmentBar(QWidget):
    """Полоса с бегунком: слева насыщенный янтарно-зелёный, справа плавный сход в прозрачность (эффект «хвоста»)."""
    SEGMENT_WIDTH = 35  # длина бегунка в пикселях

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(10)
        self._value = 0.0  # 0–100, позиция отрезка (float для плавности)

    def setValue(self, value: float):
        self._value = max(0.0, min(100.0, float(value)))
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        qp.setRenderHint(QPainter.SmoothPixmapTransform)
        w, h = self.width(), self.height()
        if w < self.SEGMENT_WIDTH or h <= 0:
            return
        # Фон (трек)
        qp.setPen(Qt.NoPen)
        qp.setBrush(QColor("#2a2a2a"))
        qp.drawRoundedRect(0, 0, w, h, 5, 5)
        # Бегунок: позиция в пикселях с дробной частью для плавного движения
        x = (self._value / 100.0) * (w - self.SEGMENT_WIDTH)
        grad = QLinearGradient(x, 0, x + self.SEGMENT_WIDTH, 0)
        head = QColor(154, 205, 50)   # насыщенный янтарно-зелёный #9acd32
        head.setAlpha(255)
        tail = QColor(184, 212, 168)  # тот же тон
        tail.setAlpha(0)
        grad.setColorAt(0, head)
        grad.setColorAt(1, tail)
        qp.setBrush(QBrush(grad))
        qp.drawRoundedRect(QRectF(x, 0, self.SEGMENT_WIDTH, h), 5, 5)
        qp.end()


class MainWindow(QMainWindow):
    """Главное окно приложения."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChatList - Сравнение ответов нейросетей")
        self.setGeometry(100, 100, 1200, 800)
        
        # Временная таблица результатов (в памяти)
        self.temp_results: List[Dict] = []
        self.current_prompt_id: Optional[int] = None
        self.current_prompt_text: str = ""
        
        # Инициализация БД
        db.init_database()
        
        # Инициализация логгера
        self.logger = get_logger()
        log_action(self.logger, "Запуск приложения", f"Версия {__version__}")
        
        # Создание интерфейса
        self.init_ui()
        
        # Загрузка активных моделей в комбобокс
        self.load_models()
    
    def showEvent(self, event):
        """При первом показе окна применяем тёмную полосу заголовка на Windows, если тема тёмная."""
        super().showEvent(event)
        current_theme = db.get_setting(THEME_SETTING_KEY) or THEME_SYSTEM
        if current_theme == THEME_DARK:
            app = QApplication.instance()
            if app:
                _set_windows_dark_title_bar(app, dark=True)
    
    def init_ui(self):
        """Инициализация пользовательского интерфейса."""
        # Создание меню
        self.create_menu()
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Панель ввода промпта
        prompt_group = QWidget()
        prompt_layout = QVBoxLayout()
        prompt_group.setLayout(prompt_layout)
        
        prompt_layout.addWidget(QLabel("Промпт:"))
        
        # Выбор сохранённого промпта
        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel("Активные модели:"))
        self.prompt_combo = QComboBox()
        self.prompt_combo.currentIndexChanged.connect(self.on_prompt_selected)
        select_button = QPushButton("Открыть историю")
        select_button.clicked.connect(self.show_prompts_dialog)
        select_layout.addWidget(self.prompt_combo)
        select_layout.addWidget(select_button)
        prompt_layout.addLayout(select_layout)
        
        # Поле ввода промпта с кнопкой улучшения
        prompt_input_layout = QVBoxLayout()
        
        # Кнопка улучшения промпта
        improve_button_layout = QHBoxLayout()
        improve_button_layout.addStretch()
        self.improve_prompt_button = QPushButton("✨ Улучшить промт")
        self.improve_prompt_button.setToolTip("Улучшить промпт с помощью AI")
        self.improve_prompt_button.clicked.connect(self.show_improve_prompt_dialog)
        improve_button_layout.addWidget(self.improve_prompt_button)
        prompt_input_layout.addLayout(improve_button_layout)
        
        # Поле ввода промпта (адаптивная высота: минимум 3 строки, растягивается при увеличении окна)
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Введите ваш промпт здесь...")
        self.prompt_edit.setMinimumHeight(72)
        self.prompt_edit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.prompt_edit.setToolTip("Введите текст промпта, который будет отправлен во все активные модели")
        prompt_input_layout.addWidget(self.prompt_edit)
        
        prompt_layout.addLayout(prompt_input_layout)
        
        # Поле для тегов
        tags_layout = QHBoxLayout()
        tags_layout.addWidget(QLabel("Теги (через запятую):"))
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("например: наука, физика")
        tags_layout.addWidget(self.tags_edit)
        prompt_layout.addLayout(tags_layout)
        
        # Кнопка отправки
        self.send_button = QPushButton("Отправить")
        self.send_button.clicked.connect(self.send_requests)
        self.send_button.setToolTip("Отправить промпт во все активные модели")
        prompt_layout.addWidget(self.send_button)
        
        # Полоса ожидания: движущийся прямоугольник с градиентом (под кнопкой «Отправить»)
        self.request_progress_bar = MovingSegmentBar(self)
        self.request_progress_bar.setValue(0)
        self.request_progress_bar.setVisible(False)
        prompt_layout.addWidget(self.request_progress_bar)
        self.request_progress_timer = QTimer(self)
        self.request_progress_timer.timeout.connect(self._animate_request_progress)
        self._request_progress_value = 0
        
        # Верхний блок (промпт) — доля 1 при растяжении
        main_layout.addWidget(prompt_group, 1)

        # Таблица результатов
        results_label = QLabel("Результаты:")
        main_layout.addWidget(results_label)

        self.results_table = QTableWidget()
        self.results_table.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Модель", "Ответ", "Выбрано"])
        self.results_table.setWordWrap(True)
        # Включаем автоматическое изменение высоты строк
        self.results_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        # Настраиваем растяжение колонок
        self.results_table.horizontalHeader().setStretchLastSection(False)  # Отключаем растяжение последней секции
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # Колонка "Ответ" растягивается
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)  # Колонка "Выбрано" фиксированной ширины
        self.results_table.setColumnWidth(2, 30)  # Устанавливаем ширину 30 пикселей для колонки "Выбрано"
        # Устанавливаем ширину вертикального заголовка (номера строк) в 20 пикселей
        self.results_table.verticalHeader().setFixedWidth(20)  # Ширина столбца с номерами строк
        # Минимальная высота строки для колонки "Ответ" (примерно 4–5 строк текста)
        self.results_table.verticalHeader().setDefaultSectionSize(100)
        # Таблица результатов — доля 2, забирает оставшееся пространство по высоте
        main_layout.addWidget(self.results_table, 2)
        
        # Кнопки управления результатами
        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton("Сохранить выбранные")
        self.save_button.clicked.connect(self.save_selected_results)
        self.save_button.setEnabled(False)
        self.save_button.setToolTip("Сохранить выбранные результаты в базу данных")
        
        self.clear_button = QPushButton("Очистить")
        self.clear_button.clicked.connect(self.clear_results)
        self.clear_button.setToolTip("Очистить таблицу результатов")
        
        self.new_request_button = QPushButton("Новый запрос")
        self.new_request_button.clicked.connect(self.new_request)
        self.new_request_button.setToolTip("Очистить форму и подготовиться к новому запросу")
        
        self.open_button = QPushButton("Открыть")
        self.open_button.clicked.connect(self.open_response_markdown)
        self.open_button.setToolTip("Открыть выбранный ответ в форматированном Markdown")
        self.open_button.setEnabled(False)
        
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.open_button)
        buttons_layout.addWidget(self.clear_button)
        buttons_layout.addWidget(self.new_request_button)
        buttons_layout.addStretch()
        main_layout.addLayout(buttons_layout)
        
        # Статусная строка
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Готово")
        
        # Индикатор загрузки
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.statusBar.addPermanentWidget(self.progress_bar)
    
    def create_menu(self):
        """Создать меню приложения."""
        menubar = self.menuBar()
        
        # Меню "Модели"
        models_menu = menubar.addMenu("Модели")
        manage_models_action = QAction("Управление моделями", self)
        manage_models_action.triggered.connect(self.show_models_dialog)
        models_menu.addAction(manage_models_action)
        
        # Меню "Промпты"
        prompts_menu = menubar.addMenu("Промпты")
        view_prompts_action = QAction("История промптов", self)
        view_prompts_action.triggered.connect(self.show_prompts_dialog)
        prompts_menu.addAction(view_prompts_action)
        
        # Меню "Результаты"
        results_menu = menubar.addMenu("Результаты")
        view_results_action = QAction("Сохранённые результаты", self)
        view_results_action.triggered.connect(self.show_results_dialog)
        results_menu.addAction(view_results_action)
        
        # Подменю экспорта
        export_menu = results_menu.addMenu("Экспорт")
        export_markdown_action = QAction("Экспорт в Markdown", self)
        export_markdown_action.triggered.connect(self.export_to_markdown)
        export_menu.addAction(export_markdown_action)
        
        export_json_action = QAction("Экспорт в JSON", self)
        export_json_action.triggered.connect(self.export_to_json)
        export_menu.addAction(export_json_action)
        
        # Меню "Настройки"
        settings_menu = menubar.addMenu("Настройки")
        
        # Пункт "Настройки..." - открывает диалог со всеми настройками
        settings_dialog_action = QAction("Настройки...", self)
        settings_dialog_action.triggered.connect(self.show_settings_dialog)
        settings_menu.addAction(settings_dialog_action)
        
        settings_menu.addSeparator()
        
        disable_sounds_action = QAction("Отключить звуки", self)
        disable_sounds_action.setCheckable(True)
        sounds_enabled = db.get_setting('sounds_enabled')
        if sounds_enabled is None:
            sounds_enabled = 'true'
        disable_sounds_action.setChecked(sounds_enabled != 'true')
        disable_sounds_action.triggered.connect(self.toggle_sounds)
        settings_menu.addAction(disable_sounds_action)
        
        # Меню "Справка"
        help_menu = menubar.addMenu("Справка")
        about_action = QAction("О программе", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
    
    def load_models(self):
        """Загрузить список активных моделей в комбобокс."""
        # Загружаем только активные модели (is_active=1)
        active_models = get_active_models_list()
        self.prompt_combo.clear()
        self.prompt_combo.addItem("Активные модели", None)
        for model in active_models:
            self.prompt_combo.addItem(model.name, model.id)
    
    def on_prompt_selected(self, index):
        """Обработчик выбора модели из комбобокса."""
        # Этот комбобокс теперь показывает активные модели, а не промпты
        # Выбор модели не влияет на поле ввода промпта
        # История промптов доступна через кнопку "Открыть историю"
        pass
    
    def show_prompts_dialog(self):
        """Показать диалог истории промптов."""
        dialog = PromptsDialog(self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_prompt_id:
            prompt = db.get_prompt_by_id(dialog.selected_prompt_id)
            if prompt:
                self.prompt_edit.setText(prompt['prompt'])
                self.tags_edit.setText(prompt['tags'] or '')
                # Сбрасываем выбор в комбобоксе моделей (выбираем "Новый промпт")
                self.prompt_combo.setCurrentIndex(0)
    
    def show_improve_prompt_dialog(self):
        """Показать диалог улучшения промпта."""
        # Получаем текущий текст промпта
        prompt_text = self.prompt_edit.toPlainText().strip()
        
        if not prompt_text:
            QMessageBox.warning(self, "Ошибка", "Введите промпт для улучшения")
            return
        
        # Получаем список активных моделей
        models = get_active_models_list()
        
        if not models:
            QMessageBox.warning(self, "Ошибка", "Нет активных моделей для улучшения промпта")
            return
        
        # Создаем и показываем диалог
        dialog = PromptImproverDialog(self, prompt_text, models)
        
        if dialog.exec_() == QDialog.Accepted and dialog.selected_text:
            # Подставляем выбранный текст в поле ввода
            self.prompt_edit.setPlainText(dialog.selected_text)
            # Устанавливаем фокус на поле ввода
            self.prompt_edit.setFocus()
    
    def show_models_dialog(self):
        """Показать диалог управления моделями."""
        dialog = ModelsDialog(self)
        dialog.exec_()
        self.load_models()  # Обновляем список моделей
    
    def show_results_dialog(self):
        """Показать диалог сохранённых результатов."""
        dialog = ResultsDialog(self)
        dialog.exec_()
    
    def _animate_request_progress(self):
        """Плавная анимация полосы ожидания (~50 FPS, малый шаг)."""
        self._request_progress_value += 0.4  # полный цикл ~5 с при интервале 20 мс
        if self._request_progress_value >= 100:
            self._request_progress_value = 0.0
        self.request_progress_bar.setValue(self._request_progress_value)
    
    def send_requests(self):
        """Отправить запросы ко всем активным моделям."""
        prompt_text = self.prompt_edit.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "Ошибка", "Введите промпт")
            return
        
        # Получаем активные модели
        active_models = get_active_models_list()
        if not active_models:
            QMessageBox.warning(self, "Ошибка", "Нет активных моделей. Добавьте модели в меню 'Модели'")
            return
        
        # Сохраняем промпт в БД (оригинальный, без дополнений)
        tags = self.tags_edit.text().strip() or None
        self.current_prompt_id = db.create_prompt(prompt_text, tags)
        self.current_prompt_text = prompt_text
        
        # Обновляем список активных моделей в комбобоксе
        self.load_models()
        
        # Автоматически добавляем инструкцию о форматировании Markdown
        enhanced_prompt = prompt_text + MARKDOWN_FORMATTING_INSTRUCTION
        
        log_action(self.logger, "Отправка запросов", f"К {len(active_models)} моделям")
        
        # Очищаем предыдущие результаты
        self.clear_results()
        
        # Показываем индикатор загрузки
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(active_models))
        self.progress_bar.setValue(0)
        self.send_button.setEnabled(False)
        self.statusBar.showMessage(f"Отправка запросов к {len(active_models)} моделям...")
        
        # Полоса ожидания под кнопкой: плавная анимация (20 мс ≈ 50 FPS, дробный шаг позиции)
        self._request_progress_value = 0.0
        self.request_progress_bar.setValue(0)
        self.request_progress_bar.setVisible(True)
        self.request_progress_timer.start(20)
        
        # Создаём поток для выполнения запросов (с дополненным промптом)
        self.request_thread = RequestThread(active_models, enhanced_prompt)
        self.request_thread.finished.connect(self.on_requests_finished)
        self.request_thread.start()
    
    def on_requests_finished(self, results: List[Dict]):
        """Обработчик завершения запросов."""
        self.progress_bar.setVisible(False)
        self.request_progress_timer.stop()
        self.request_progress_bar.setVisible(False)
        self.send_button.setEnabled(True)
        
        # Обновляем таблицу результатов
        self.results_table.setRowCount(len(results))
        
        for row, result in enumerate(results):
            model = result['model']
            success = result['success']
            response = result['response']
            
            # Логируем результат
            log_request(self.logger, model.name, self.current_prompt_text, success, 
                      response if success else "", response if not success else "")
            
            # Название модели
            model_item = QTableWidgetItem(model.name)
            if not success:
                model_item.setForeground(Qt.red)
            self.results_table.setItem(row, 0, model_item)
            
            # Ответ - убираем Markdown-разметку для отображения в таблице
            response_text = response if success else f"Ошибка: {response}"
            # В таблице показываем обычный текст без форматирования
            plain_text = strip_markdown(response_text) if success else response_text
            response_item = QTableWidgetItem(plain_text)
            response_item.setTextAlignment(Qt.AlignTop | Qt.AlignLeft)
            # Включаем перенос текста для ячейки
            response_item.setFlags(response_item.flags() | Qt.TextWordWrap)
            self.results_table.setItem(row, 1, response_item)
            # Высота строки не менее 100 px (несколько строк текста)
            self.results_table.setRowHeight(row, max(100, self.results_table.rowHeight(row)))
            
            # Чекбокс
            checkbox = QCheckBox()
            checkbox.setChecked(success)  # По умолчанию выбираем успешные ответы
            checkbox.setEnabled(success)  # Отключаем для ошибок
            self.results_table.setCellWidget(row, 2, checkbox)
            
            # Сохраняем во временную таблицу (сохраняем оригинальный текст с Markdown для диалога "Открыть")
            self.temp_results.append({
                'model_name': model.name,
                'response_text': response_text,  # Оригинальный текст с Markdown
                'plain_text': plain_text,  # Текст без Markdown для таблицы
                'selected': success,
                'success': success
            })
        
        self.results_table.resizeColumnsToContents()
        self.save_button.setEnabled(True)
        self.open_button.setEnabled(True)
        success_count = len([r for r in results if r['success']])
        self.statusBar.showMessage(f"Получено {success_count} ответов из {len(results)}")
        log_action(self.logger, "Запросы завершены", f"Успешно: {success_count}/{len(results)}")
    
    def save_selected_results(self):
        """Сохранить выбранные результаты в БД."""
        if not self.current_prompt_id:
            QMessageBox.warning(self, "Ошибка", "Нет активного промпта")
            return
        
        saved_count = 0
        for row in range(self.results_table.rowCount()):
            checkbox = self.results_table.cellWidget(row, 2)
            if checkbox and checkbox.isChecked():
                model_name = self.results_table.item(row, 0).text()
                # Берём оригинальный текст с Markdown из временной таблицы
                if row < len(self.temp_results) and self.temp_results[row].get('response_text'):
                    response_text = self.temp_results[row]['response_text']
                else:
                    # Если нет в временной таблице, берём из ячейки
                    response_text = self.results_table.item(row, 1).text()
                
                # Пропускаем ошибки
                if response_text.startswith("Ошибка:"):
                    continue
                
                db.save_result(self.current_prompt_id, model_name, response_text)
                saved_count += 1
        
        if saved_count > 0:
            log_action(self.logger, "Сохранение результатов", f"Сохранено: {saved_count}")
            QMessageBox.information(self, "Успех", f"Сохранено результатов: {saved_count}")
            self.clear_results()
        else:
            QMessageBox.warning(self, "Ошибка", "Выберите результаты для сохранения")
    
    def clear_results(self):
        """Очистить таблицу результатов."""
        self.results_table.setRowCount(0)
        self.temp_results.clear()
        self.save_button.setEnabled(False)
        self.open_button.setEnabled(False)
    
    def open_response_markdown(self):
        """Открыть выбранный ответ в окне с форматированным Markdown."""
        row = self.results_table.currentRow()
        if row < 0 and self.results_table.rowCount() > 0:
            row = 0
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Нет результатов. Сначала отправьте запрос.")
            return
        
        model_name = self.results_table.item(row, 0).text()
        # Получаем оригинальный текст с Markdown из временной таблицы
        if row < len(self.temp_results) and self.temp_results[row].get('response_text'):
            response_text = self.temp_results[row]['response_text']
        else:
            # Если нет в временной таблице, берём из ячейки (но там уже без Markdown)
            response_text = self.results_table.item(row, 1).text()
        title = f"Ответ: {model_name}"
        dialog = MarkdownViewerDialog(self, title=title, content=response_text)
        dialog.exec_()
    
    def new_request(self):
        """Подготовка к новому запросу."""
        self.prompt_edit.clear()
        self.tags_edit.clear()
        self.prompt_combo.setCurrentIndex(0)
        self.clear_results()
        self.current_prompt_id = None
        self.statusBar.showMessage("Готово к новому запросу")
    
    def toggle_sounds(self, checked: bool):
        """Переключить звуки приложения."""
        db.set_setting('sounds_enabled', 'false' if checked else 'true')
        if checked:
            # Отключаем звуки через переменную окружения
            os.environ['QT_AUDIO_DEVICE'] = 'none'
            QMessageBox.information(self, "Настройки", "Звуки отключены. Перезапустите приложение для применения изменений.")
        else:
            # Включаем звуки
            if 'QT_AUDIO_DEVICE' in os.environ:
                del os.environ['QT_AUDIO_DEVICE']
            QMessageBox.information(self, "Настройки", "Звуки включены. Перезапустите приложение для применения изменений.")
    
    def set_theme(self, theme: str) -> None:
        """Установить тему оформления (светлая / тёмная / системная)."""
        db.set_setting(THEME_SETTING_KEY, theme)
        app = QApplication.instance()
        if app:
            apply_theme(app, theme)
            log_action(self.logger, "Смена темы", theme)
            self.statusBar.showMessage(f"Тема изменена: {'Светлая' if theme == THEME_LIGHT else 'Тёмная' if theme == THEME_DARK else 'Системная'}", 3000)
    
    def show_settings_dialog(self):
        """Показать диалог настроек."""
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # Сохраняем тему
            selected_theme = dialog.get_selected_theme()
            self.set_theme(selected_theme)
            
            # Сохраняем размер шрифта
            font_size = dialog.get_font_size()
            db.set_setting('font_size', str(font_size))
            
            log_action(self.logger, "Изменение настроек", f"Тема: {selected_theme}, Размер шрифта: {font_size}px")
            QMessageBox.information(
                self, 
                "Настройки", 
                f"Настройки сохранены.\n\n"
                f"Тема: {'Светлая' if selected_theme == THEME_LIGHT else 'Тёмная' if selected_theme == THEME_DARK else 'Системная'}\n"
                f"Размер шрифта: {font_size}px\n\n"
                f"Изменение размера шрифта вступит в силу после перезапуска приложения."
            )
    
    def show_about_dialog(self):
        """Показать диалог 'О программе'."""
        dialog = AboutDialog(self)
        dialog.exec_()
    
    def export_to_markdown(self):
        """Экспортировать текущие результаты в Markdown."""
        if not self.temp_results:
            QMessageBox.warning(self, "Ошибка", "Нет результатов для экспорта")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить как Markdown",
            f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            "Markdown Files (*.md);;All Files (*)"
        )
        
        if file_path:
            success = export_to_markdown(self.temp_results, self.current_prompt_text, file_path)
            if success:
                log_action(self.logger, "Экспорт в Markdown", f"Файл: {file_path}")
                QMessageBox.information(self, "Успех", f"Результаты экспортированы в {file_path}")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось экспортировать результаты")
    
    def export_to_json(self):
        """Экспортировать текущие результаты в JSON."""
        if not self.temp_results:
            QMessageBox.warning(self, "Ошибка", "Нет результатов для экспорта")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить как JSON",
            f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            success = export_to_json(self.temp_results, self.current_prompt_text, file_path)
            if success:
                log_action(self.logger, "Экспорт в JSON", f"Файл: {file_path}")
                QMessageBox.information(self, "Успех", f"Результаты экспортированы в {file_path}")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось экспортировать результаты")


def main():
    """Главная функция приложения."""
    # Инициализируем БД для проверки настроек
    db.init_database()
    
    # Проверяем настройку звуков
    sounds_enabled = db.get_setting('sounds_enabled')
    if sounds_enabled == 'false':
        # Отключаем звуки через переменную окружения
        os.environ['QT_AUDIO_DEVICE'] = 'none'
    
    # Отключаем системные звуки приложения
    QCoreApplication.setAttribute(Qt.AA_DisableWindowContextHelpButton)
    
    app = QApplication(sys.argv)
    
    # Устанавливаем иконку приложения
    icon_path = "app.ico"
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # Применяем сохранённую тему (светлая / тёмная / системная)
    saved_theme = db.get_setting(THEME_SETTING_KEY) or THEME_SYSTEM
    apply_theme(app, saved_theme)
    
    # Применяем сохранённый размер шрифта
    font_size_str = db.get_setting('font_size')
    if font_size_str:
        try:
            font_size = int(font_size_str)
            if 8 <= font_size <= 24:
                app_font = QFont()
                app_font.setPointSize(font_size)
                app.setFont(app_font)
        except ValueError:
            pass  # Используем размер по умолчанию
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
