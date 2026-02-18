"""
Тестовая программа для просмотра и редактирования SQLite базы данных.
Отображает список таблиц и позволяет просматривать/редактировать данные с пагинацией.
"""
import sys
import sqlite3
import platform
import json
import os
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
    QFileDialog, QComboBox, QMessageBox, QDialog, QFormLayout,
    QDialogButtonBox, QSpinBox, QTextEdit, QTabWidget, QGroupBox, QToolBar, QSizePolicy,
    QAbstractItemView, QScrollArea, QDoubleSpinBox, QMenu, QHeaderView
)
from PyQt5.QtCore import Qt, QObject, QEvent
from PyQt5.QtGui import QFont, QMouseEvent
from typing import List, Dict, Optional, Tuple


class RecordEditorDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        title: str,
        schema: List[Dict],
        values: Dict,
        primary_key: Optional[str],
        dark_mode: bool,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.schema = schema
        self.primary_key = primary_key
        self.widgets: Dict[str, QWidget] = {}

        root_layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        root_layout.addWidget(scroll)

        container = QWidget()
        form = QFormLayout(container)
        scroll.setWidget(container)

        for col in schema:
            name = col["name"]
            col_type = (col.get("type") or "").upper()
            is_pk = bool(col.get("pk"))

            if is_pk:
                w = QLineEdit()
                w.setReadOnly(True)
                w.setText("" if values.get(name) is None else str(values.get(name)))
            elif "REAL" in col_type or "FLOAT" in col_type or "DOUBLE" in col_type:
                w = QDoubleSpinBox()
                w.setDecimals(6)
                w.setMinimum(-1e12)
                w.setMaximum(1e12)
                try:
                    w.setValue(float(values.get(name) or 0))
                except Exception:
                    w.setValue(0.0)
            elif "INTEGER" in col_type or "INT" in col_type:
                w = QSpinBox()
                w.setMinimum(-2147483648)
                w.setMaximum(2147483647)
                try:
                    w.setValue(int(values.get(name) or 0))
                except Exception:
                    w.setValue(0)
            elif "BLOB" in col_type:
                w = QTextEdit()
                w.setMaximumHeight(120)
                w.setPlainText("" if values.get(name) is None else str(values.get(name)))
            else:
                w = QLineEdit()
                w.setText("" if values.get(name) is None else str(values.get(name)))

            self.widgets[name] = w
            form.addRow(f"{name}:", w)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root_layout.addWidget(buttons)

        self.resize(640, 520)

    def get_values_for_update(self) -> Dict:
        out: Dict[str, object] = {}
        for col in self.schema:
            name = col["name"]
            if col.get("pk"):
                continue
            w = self.widgets.get(name)
            if w is None:
                continue
            if isinstance(w, QDoubleSpinBox):
                out[name] = float(w.value())
            elif isinstance(w, QSpinBox):
                out[name] = int(w.value())
            elif isinstance(w, QTextEdit):
                out[name] = w.toPlainText()
            elif isinstance(w, QLineEdit):
                out[name] = w.text()
            else:
                try:
                    out[name] = w.text()  # type: ignore[attr-defined]
                except Exception:
                    out[name] = ""
        return out


class DatabaseViewer(QMainWindow):
    """Главное окно приложения для просмотра SQLite базы данных."""
    
    def __init__(self):
        super().__init__()
        self.db_path = None
        self.conn = None
        self.current_table = None
        self.current_page = 0
        self.rows_per_page = 10
        self.dark_mode = False
        # Путь к файлу истории
        self.history_file = Path.home() / ".test-db-history.json"
        # Флаг для предотвращения рекурсии при обновлении истории
        self.updating_history = False
        self.init_ui()
    
    def init_ui(self):
        """Инициализация пользовательского интерфейса."""
        self.setWindowTitle("Просмотр SQLite базы данных")
        self.setGeometry(100, 100, 1200, 800)
        
        # Создаем тулбар для переключателя темы
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        
        # Добавляем отступ слева
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)
        
        # Кнопка переключателя темы
        self.theme_btn = QPushButton("🌙")
        self.theme_btn.setToolTip("Переключить тему (Светлая/Темная)")
        self.theme_btn.setFixedSize(40, 30)
        self.theme_btn.clicked.connect(self.toggle_theme)
        toolbar.addWidget(self.theme_btn)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        # Устанавливаем обработчик клика для снятия выделения
        central_widget.mousePressEvent = self.on_central_widget_clicked
        layout = QVBoxLayout(central_widget)
        
        # Верхняя панель: выбор файла
        file_group = QGroupBox("Файл базы данных")
        file_layout = QVBoxLayout()
        
        # Первая строка: поле файла и кнопки
        file_row_layout = QHBoxLayout()
        
        self.file_label = QLabel("файл не выбран")
        self.file_label.setStyleSheet("color: gray;")
        file_row_layout.addWidget(self.file_label)
        
        self.select_file_btn = QPushButton("Выбрать файл БД")
        self.select_file_btn.clicked.connect(self.select_database_file)
        file_row_layout.addWidget(self.select_file_btn)
        
        file_layout.addLayout(file_row_layout)
        
        # Вторая строка: история файлов
        history_row_layout = QHBoxLayout()
        history_row_layout.addWidget(QLabel("История:"))
        
        self.history_combo = QComboBox()
        self.history_combo.setEditable(False)
        # Временно отключаем сигнал при загрузке истории, чтобы избежать автоматической загрузки файла
        self.loading_history = False
        self.history_combo.currentIndexChanged.connect(self.on_history_index_changed)
        self.history_combo.setMinimumWidth(400)
        history_row_layout.addWidget(self.history_combo)
        
        self.load_from_history_btn = QPushButton("📂 Загрузить")
        self.load_from_history_btn.setToolTip("Загрузить выбранный файл из истории")
        self.load_from_history_btn.clicked.connect(self.load_selected_from_history)
        self.load_from_history_btn.setEnabled(False)
        history_row_layout.addWidget(self.load_from_history_btn)
        
        self.remove_from_history_btn = QPushButton("🗑️ Удалить из истории")
        self.remove_from_history_btn.setToolTip("Удалить выбранный файл из истории")
        self.remove_from_history_btn.clicked.connect(self.remove_from_history)
        self.remove_from_history_btn.setEnabled(False)
        history_row_layout.addWidget(self.remove_from_history_btn)
        
        file_layout.addLayout(history_row_layout)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Панель выбора таблицы
        table_group = QGroupBox("Выбор таблицы")
        table_layout = QHBoxLayout()
        
        table_layout.addWidget(QLabel("Таблица:"))
        self.table_combo = QComboBox()
        self.table_combo.currentTextChanged.connect(self.on_table_changed)
        table_layout.addWidget(self.table_combo)
        
        self.open_table_btn = QPushButton("Открыть")
        self.open_table_btn.setEnabled(False)
        self.open_table_btn.clicked.connect(self.open_table)
        table_layout.addWidget(self.open_table_btn)
        
        table_group.setLayout(table_layout)
        layout.addWidget(table_group)
        
        # Вкладки для CRUD операций
        self.tabs = QTabWidget()
        
        # Вкладка просмотра
        self.view_tab = QWidget()
        view_layout = QVBoxLayout(self.view_tab)
        
        # Панель пагинации
        pagination_layout = QHBoxLayout()
        self.pagination_label = QLabel("")
        pagination_layout.addWidget(self.pagination_label)
        
        # Кнопка обновления данных
        self.refresh_btn = QPushButton("🔄 Обновить")
        self.refresh_btn.setToolTip("Обновить данные из базы данных")
        self.refresh_btn.clicked.connect(self.refresh_table_data)
        self.refresh_btn.setEnabled(False)  # Изначально неактивна
        pagination_layout.addWidget(self.refresh_btn)
        
        pagination_layout.addStretch()
        
        self.first_btn = QPushButton("⏮ Первая")
        self.first_btn.clicked.connect(self.go_to_first_page)
        pagination_layout.addWidget(self.first_btn)
        
        self.prev_btn = QPushButton("◀ Предыдущая")
        self.prev_btn.clicked.connect(self.go_to_prev_page)
        pagination_layout.addWidget(self.prev_btn)
        
        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(1)
        self.page_spin.valueChanged.connect(self.on_page_changed)
        pagination_layout.addWidget(self.page_spin)
        
        pagination_layout.addWidget(QLabel("из"))
        self.total_pages_label = QLabel("1")
        pagination_layout.addWidget(self.total_pages_label)
        
        self.next_btn = QPushButton("Следующая ▶")
        self.next_btn.clicked.connect(self.go_to_next_page)
        pagination_layout.addWidget(self.next_btn)
        
        self.last_btn = QPushButton("Последняя ⏭")
        self.last_btn.clicked.connect(self.go_to_last_page)
        pagination_layout.addWidget(self.last_btn)
        
        pagination_layout.addStretch()
        
        rows_per_page_layout = QHBoxLayout()
        rows_per_page_layout.addWidget(QLabel("Записей на странице:"))
        self.rows_per_page_spin = QSpinBox()
        self.rows_per_page_spin.setMinimum(5)
        self.rows_per_page_spin.setMaximum(100)
        self.rows_per_page_spin.setValue(10)
        self.rows_per_page_spin.setSingleStep(5)
        self.rows_per_page_spin.valueChanged.connect(self.on_rows_per_page_changed)
        rows_per_page_layout.addWidget(self.rows_per_page_spin)
        rows_per_page_layout.addStretch()
        
        view_layout.addLayout(pagination_layout)
        view_layout.addLayout(rows_per_page_layout)
        
        # Таблица данных
        self.table_widget = QTableWidget()
        # Настройка выделения целых строк вместо отдельных ячеек
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        # Настройка заголовка таблицы
        header = self.table_widget.horizontalHeader()
        header.setStretchLastSection(False)
        # Обработчик клика по пустому месту для снятия выделения
        self.table_widget.viewport().installEventFilter(self)
        view_layout.addWidget(self.table_widget, 1)  # stretch factor = 1 для растягивания
        
        self.tabs.addTab(self.view_tab, "📖 Просмотр")
        
        # Вкладка создания
        self.create_tab = QWidget()
        create_layout = QVBoxLayout(self.create_tab)
        self.create_form_layout = QFormLayout()
        self.create_fields = {}
        create_layout.addLayout(self.create_form_layout)
        create_layout.addStretch()
        
        create_btn = QPushButton("✅ Создать запись")
        create_btn.clicked.connect(self.create_record)
        create_layout.addWidget(create_btn)
        
        self.tabs.addTab(self.create_tab, "➕ Создать")
        
        # Вкладка редактирования
        self.edit_tab = QWidget()
        edit_layout = QVBoxLayout(self.edit_tab)
        
        edit_select_layout = QHBoxLayout()
        edit_select_layout.addWidget(QLabel("Выберите запись:"))
        self.edit_combo = QComboBox()
        self.edit_combo.currentIndexChanged.connect(self.on_edit_record_selected)
        edit_select_layout.addWidget(self.edit_combo)
        edit_layout.addLayout(edit_select_layout)

        self.open_edit_dialog_btn = QPushButton("✏️ Редактировать строку…")
        self.open_edit_dialog_btn.clicked.connect(self.open_edit_dialog)
        edit_layout.addWidget(self.open_edit_dialog_btn)
        edit_layout.addStretch()
        
        self.tabs.addTab(self.edit_tab, "✏️ Редактировать")
        
        # Вкладка удаления
        self.delete_tab = QWidget()
        delete_layout = QVBoxLayout(self.delete_tab)
        
        delete_select_layout = QHBoxLayout()
        delete_select_layout.addWidget(QLabel("Выберите запись:"))
        self.delete_combo = QComboBox()
        self.delete_combo.currentIndexChanged.connect(self.on_delete_record_selected)
        delete_select_layout.addWidget(self.delete_combo)
        delete_layout.addLayout(delete_select_layout)
        
        delete_info_label = QLabel("Информация о записи:")
        delete_layout.addWidget(delete_info_label)
        
        self.delete_info_text = QTextEdit()
        self.delete_info_text.setReadOnly(True)
        delete_layout.addWidget(self.delete_info_text)
        
        delete_btn = QPushButton("🗑️ Удалить запись")
        delete_btn.setStyleSheet("background-color: #dc3545; color: white;")
        delete_btn.clicked.connect(self.delete_record)
        delete_layout.addWidget(delete_btn)
        
        self.tabs.addTab(self.delete_tab, "🗑️ Удалить")
        
        layout.addWidget(self.tabs)
        
        # Изначально вкладки неактивны
        self.tabs.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        
        # Загружаем историю после создания всех элементов UI
        self.load_history()
        
        # Применяем начальную тему
        self.apply_theme()
    
    def showEvent(self, event):
        """Обработчик события показа окна."""
        super().showEvent(event)
        # Применяем тему заголовка после показа окна
        if self.dark_mode:
            self.apply_window_theme(True)
        else:
            self.apply_window_theme(False)
    
    def resizeEvent(self, event):
        """Обработчик изменения размера окна."""
        super().resizeEvent(event)
        # Пересчитываем ширину колонок при изменении размера окна
        if self.table_widget and self.current_table:
            self.adjust_column_widths()
    
    def apply_window_theme(self, dark: bool):
        """Применить тему к заголовку окна Windows."""
        if platform.system() == "Windows":
            try:
                import ctypes
                from ctypes import wintypes
                # Используем Windows API для темной темы заголовка (Windows 10/11)
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                hwnd = int(self.winId())
                value = ctypes.c_int(1 if dark else 0)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    wintypes.HWND(hwnd),
                    DWMWA_USE_IMMERSIVE_DARK_MODE,
                    ctypes.byref(value),
                    ctypes.sizeof(value)
                )
            except Exception:
                pass  # Если не удалось, продолжаем без изменения заголовка
    
    def load_history(self):
        """Загрузить историю файлов из JSON."""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                    # Фильтруем только существующие файлы
                    original_history = history.copy()
                    history = [path for path in history if os.path.exists(path)]
                    # Сохраняем отфильтрованную историю
                    if len(history) != len(original_history):
                        self.save_history(history)
            else:
                history = []
        except Exception:
            history = []
        
        # Временно отключаем сигнал при загрузке истории
        self.loading_history = True
        self.history_combo.blockSignals(True)
        
        # Обновляем комбобокс истории
        self.history_combo.clear()
        if history:
            self.history_combo.addItems(history)
            self.remove_from_history_btn.setEnabled(True)
            self.load_from_history_btn.setEnabled(True)
        else:
            self.history_combo.addItem("(нет истории)")
            self.remove_from_history_btn.setEnabled(False)
            self.load_from_history_btn.setEnabled(False)
        
        self.history_combo.blockSignals(False)
        self.loading_history = False
    
    def save_history(self, history: Optional[List[str]] = None):
        """Сохранить историю файлов в JSON."""
        if history is None:
            # Получаем текущую историю из комбобокса
            history = []
            for i in range(self.history_combo.count()):
                item_text = self.history_combo.itemText(i)
                if item_text != "(нет истории)" and os.path.exists(item_text):
                    history.append(item_text)
        
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # Игнорируем ошибки сохранения
    
    def add_to_history(self, file_path: str):
        """Добавить файл в историю."""
        if not file_path or not os.path.exists(file_path) or self.updating_history:
            return
        
        self.updating_history = True
        try:
            # Получаем текущую историю
            history = []
            for i in range(self.history_combo.count()):
                item_text = self.history_combo.itemText(i)
                if item_text != "(нет истории)":
                    history.append(item_text)
            
            # Удаляем файл из истории, если он там есть
            if file_path in history:
                history.remove(file_path)
            
            # Добавляем в начало (последний открытый файл)
            history.insert(0, file_path)
            
            # Ограничиваем историю 10 файлами
            history = history[:10]
            
            # Обновляем комбобокс (временно отключаем сигнал)
            self.history_combo.blockSignals(True)
            self.history_combo.clear()
            if history:
                self.history_combo.addItems(history)
                self.remove_from_history_btn.setEnabled(True)
                self.load_from_history_btn.setEnabled(True)
            else:
                self.history_combo.addItem("(нет истории)")
                self.remove_from_history_btn.setEnabled(False)
                self.load_from_history_btn.setEnabled(False)
            self.history_combo.blockSignals(False)
            
            # Сохраняем в файл
            self.save_history(history)
        finally:
            self.updating_history = False
    
    def remove_from_history(self):
        """Удалить выбранный файл из истории."""
        current_text = self.history_combo.currentText()
        if current_text == "(нет истории)" or not current_text:
            return
        
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить '{os.path.basename(current_text)}' из истории?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Получаем текущую историю
            history = []
            for i in range(self.history_combo.count()):
                item_text = self.history_combo.itemText(i)
                if item_text != "(нет истории)" and item_text != current_text:
                    history.append(item_text)
            
            # Обновляем комбобокс
            self.history_combo.clear()
            if history:
                self.history_combo.addItems(history)
                self.remove_from_history_btn.setEnabled(True)
                self.load_from_history_btn.setEnabled(True)
            else:
                self.history_combo.addItem("(нет истории)")
                self.remove_from_history_btn.setEnabled(False)
                self.load_from_history_btn.setEnabled(False)
            
            # Сохраняем в файл
            self.save_history(history)
    
    def on_history_index_changed(self, index: int):
        """Обработчик изменения индекса в истории."""
        current_text = self.history_combo.currentText()
        is_valid = current_text != "(нет истории)" and current_text != ""
        self.remove_from_history_btn.setEnabled(is_valid)
        self.load_from_history_btn.setEnabled(is_valid)
    
    def load_selected_from_history(self):
        """Загрузить выбранный файл из истории."""
        file_path = self.history_combo.currentText()
        if file_path == "(нет истории)" or not file_path:
            return
        
        # Проверяем существование файла
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Ошибка", f"Файл не найден:\n{file_path}")
            # Удаляем несуществующий файл из истории
            history = []
            for i in range(self.history_combo.count()):
                item_text = self.history_combo.itemText(i)
                if item_text != "(нет истории)" and item_text != file_path:
                    history.append(item_text)
            self.save_history(history)
            self.load_history()
            return
        
        # Загружаем файл
        self.load_database_file(file_path)
    
    def load_database_file(self, file_path: str):
        """Загрузить файл базы данных."""
        try:
            # Закрываем предыдущее соединение
            if self.conn:
                self.conn.close()
            
            # Открываем новое соединение
            self.conn = sqlite3.connect(file_path)
            self.db_path = file_path
            self.file_label.setText(file_path)
            # Обновляем цвет в зависимости от темы
            if not self.dark_mode:
                self.file_label.setStyleSheet("color: black;")
            else:
                self.file_label.setStyleSheet("color: #ffffff;")
            
            # Добавляем в историю
            self.add_to_history(file_path)
            
            # Загружаем список таблиц
            self.load_tables()
            
            QMessageBox.information(self, "Успех", f"База данных загружена: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть базу данных:\n{e}")
            self.conn = None
            self.db_path = None
    
    def select_database_file(self):
        """Выбор файла базы данных."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите SQLite файл", "", "SQLite Files (*.db *.sqlite *.sqlite3);;All Files (*)"
        )
        
        if file_path:
            self.load_database_file(file_path)
    
    def load_tables(self):
        """Загрузить список таблиц из базы данных."""
        if not self.conn:
            return
        
        # Проверяем, что table_combo уже создан
        if not hasattr(self, 'table_combo') or self.table_combo is None:
            return
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            
            self.table_combo.clear()
            self.table_combo.addItems(tables)
            self.open_table_btn.setEnabled(len(tables) > 0)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить список таблиц:\n{e}")
    
    def on_table_changed(self, table_name):
        """Обработчик изменения выбранной таблицы."""
        self.current_table = table_name if table_name else None
    
    def open_table(self):
        """Открыть выбранную таблицу."""
        if not self.conn or not self.current_table:
            return
        
        self.current_page = 0
        self.load_table_data()
        self.setup_crud_forms()
        self.tabs.setEnabled(True)
        self.refresh_btn.setEnabled(True)  # Активируем кнопку обновления
    
    def refresh_table_data(self):
        """Обновить данные таблицы из базы данных."""
        if not self.conn or not self.current_table:
            QMessageBox.warning(self, "Предупреждение", "Нет открытой таблицы для обновления")
            return
        
        try:
            # Перезагружаем данные текущей страницы
            self.load_table_data()
            # Обновляем формы CRUD
            self.setup_crud_forms()
            QMessageBox.information(self, "Успех", "Данные обновлены")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить данные:\n{e}")
    
    def get_table_schema(self, table_name: str) -> List[Dict]:
        """Получить схему таблицы."""
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        return [
            {
                "name": col[1],
                "type": col[2],
                "notnull": col[3],
                "pk": col[5]
            }
            for col in columns
        ]
    
    def get_primary_key_column(self, table_name: str) -> Optional[str]:
        """Получить название колонки с первичным ключом."""
        schema = self.get_table_schema(table_name)
        for col in schema:
            if col["pk"]:
                return col["name"]
        return schema[0]["name"] if schema else None
    
    def get_table_data(self, table_name: str, limit: int, offset: int) -> Tuple[List[Dict], int]:
        """Получить данные из таблицы с пагинацией."""
        cursor = self.conn.cursor()
        cursor.row_factory = sqlite3.Row
        
        # Общее количество записей
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_count = cursor.fetchone()[0]
        
        # Данные с пагинацией
        cursor.execute(f"SELECT * FROM {table_name} LIMIT ? OFFSET ?", (limit, offset))
        rows = cursor.fetchall()
        data = [dict(row) for row in rows]
        
        return data, total_count
    
    def load_table_data(self):
        """Загрузить данные таблицы в виджет."""
        if not self.conn or not self.current_table:
            return
        
        try:
            offset = self.current_page * self.rows_per_page
            data, total_count = self.get_table_data(self.current_table, self.rows_per_page, offset)
            
            # Обновляем пагинацию
            total_pages = (total_count + self.rows_per_page - 1) // self.rows_per_page if total_count > 0 else 1
            self.page_spin.setMaximum(total_pages)
            self.page_spin.setValue(self.current_page + 1)
            self.total_pages_label.setText(str(total_pages))
            self.pagination_label.setText(f"Всего записей: {total_count}")
            
            # Обновляем кнопки навигации
            self.first_btn.setEnabled(self.current_page > 0)
            self.prev_btn.setEnabled(self.current_page > 0)
            self.next_btn.setEnabled(self.current_page < total_pages - 1)
            self.last_btn.setEnabled(self.current_page < total_pages - 1)
            
            # Заполняем таблицу
            if data:
                schema = self.get_table_schema(self.current_table)
                columns = [col["name"] for col in schema]
                
                self.table_widget.setRowCount(len(data))
                self.table_widget.setColumnCount(len(columns))
                self.table_widget.setHorizontalHeaderLabels(columns)
                
                for row_idx, row_data in enumerate(data):
                    for col_idx, col_name in enumerate(columns):
                        value = row_data.get(col_name, "")
                        item = QTableWidgetItem(str(value))
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # Только для чтения
                        self.table_widget.setItem(row_idx, col_idx, item)
                
                # Настраиваем ширину колонок: id и is_active - 25px с пропорциональным масштабированием
                # Используем QTimer для отложенного вызова, чтобы таблица успела отрисоваться
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(100, self.adjust_column_widths)
            else:
                self.table_widget.setRowCount(0)
                self.table_widget.setColumnCount(0)
            
            # Обновляем комбобоксы для редактирования и удаления
            self.update_crud_combos(data)
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить данные:\n{e}")
    
    def adjust_column_widths(self):
        """Настроить ширину колонок: id и is_active - 25px с пропорциональным масштабированием."""
        if not self.table_widget or not self.current_table:
            return
        
        header = self.table_widget.horizontalHeader()
        columns = [self.table_widget.horizontalHeaderItem(i).text() 
                  for i in range(self.table_widget.columnCount())]
        
        if not columns:
            return
        
        base_width = 25  # Базовая ширина для id и is_active
        fixed_columns = ['id', 'is_active']
        
        # Определяем общую ширину таблицы
        table_width = self.table_widget.viewport().width()
        if table_width <= 0:
            table_width = self.table_widget.width() - 20  # Примерная ширина с учетом скроллбара
        
        # Подсчитываем количество колонок для растягивания и фиксированных
        stretch_columns = [col for col in columns if col.lower() not in fixed_columns]
        fixed_cols = [col for col in columns if col.lower() in fixed_columns]
        stretch_columns_count = len(stretch_columns)
        fixed_columns_count = len(fixed_cols)
        
        # Вычисляем ширину для фиксированных колонок (пропорционально размеру окна)
        if table_width > 0 and fixed_columns_count > 0:
            # Минимальная ширина для фиксированных колонок
            min_fixed_width = base_width
            # Масштабируем пропорционально размеру окна (но не меньше минимума)
            scale_factor = max(1.0, table_width / 800)  # Базовый размер окна 800px
            fixed_width = max(min_fixed_width, int(base_width * scale_factor))
            
            # Вычисляем доступную ширину для растягивающихся колонок
            available_width = table_width - (fixed_width * fixed_columns_count)
            if stretch_columns_count > 0:
                stretch_width = max(100, available_width // stretch_columns_count)
            else:
                stretch_width = 100
        else:
            fixed_width = base_width
            stretch_width = 150
        
        # Применяем настройки к каждой колонке
        for col_idx, col_name in enumerate(columns):
            col_name_lower = col_name.lower()
            if col_name_lower in fixed_columns:
                # Фиксированные колонки с минимальной шириной и пропорциональным масштабированием
                header.setSectionResizeMode(col_idx, QHeaderView.Interactive)
                header.setMinimumSectionSize(base_width)
                header.resizeSection(col_idx, fixed_width)
            else:
                # Остальные колонки растягиваются
                header.setSectionResizeMode(col_idx, QHeaderView.Stretch)
        
        # Последняя колонка растягивается на оставшееся пространство
        if len(columns) > 0:
            last_col_idx = len(columns) - 1
            if columns[last_col_idx].lower() not in fixed_columns:
                header.setSectionResizeMode(last_col_idx, QHeaderView.Stretch)
    
    def update_crud_combos(self, data: List[Dict]):
        """Обновить комбобоксы для редактирования и удаления."""
        primary_key = self.get_primary_key_column(self.current_table)
        
        self.edit_combo.clear()
        self.delete_combo.clear()
        
        for idx, row in enumerate(data):
            pk_value = row.get(primary_key, idx)
            display_text = f"ID: {pk_value} - {str(row)[:50]}..."
            self.edit_combo.addItem(display_text, idx)
            self.delete_combo.addItem(display_text, idx)
        
        # Обновляем информацию о записи для удаления
        if self.delete_combo.count() > 0:
            self.on_delete_record_selected()
    
    def setup_crud_forms(self):
        """Настроить формы для CRUD операций."""
        if not self.conn or not self.current_table:
            return
        
        schema = self.get_table_schema(self.current_table)
        
        # Очищаем формы
        self.clear_layout(self.create_form_layout)
        self.create_fields.clear()
        
        # Форма создания
        for col in schema:
            col_name = col["name"]
            col_type = col["type"].upper()
            
            if col["pk"]:
                # Пропускаем автоинкрементные PK
                continue
            
            if "INTEGER" in col_type or "INT" in col_type:
                widget = QSpinBox()
                widget.setMinimum(-2147483648)
                widget.setMaximum(2147483647)
            elif "REAL" in col_type or "FLOAT" in col_type or "DOUBLE" in col_type:
                widget = QSpinBox()
                widget.setMinimum(-999999999)
                widget.setMaximum(999999999)
                widget.setSingleStep(0.1)
            elif "TEXT" in col_type or "VARCHAR" in col_type or "CHAR" in col_type:
                widget = QLineEdit()
            elif "BLOB" in col_type:
                widget = QTextEdit()
                widget.setMaximumHeight(100)
            else:
                widget = QLineEdit()
            
            self.create_form_layout.addRow(col_name, widget)
            self.create_fields[col_name] = widget
        
        # Редактирование теперь в отдельном диалоге (как на примере)
    
    def clear_layout(self, layout):
        """Очистить layout от виджетов."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def go_to_first_page(self):
        """Перейти на первую страницу."""
        self.current_page = 0
        self.load_table_data()
    
    def go_to_prev_page(self):
        """Перейти на предыдущую страницу."""
        if self.current_page > 0:
            self.current_page -= 1
            self.load_table_data()
    
    def go_to_next_page(self):
        """Перейти на следующую страницу."""
        offset = (self.current_page + 1) * self.rows_per_page
        data, total_count = self.get_table_data(self.current_table, self.rows_per_page, offset)
        total_pages = (total_count + self.rows_per_page - 1) // self.rows_per_page if total_count > 0 else 1
        
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.load_table_data()
    
    def go_to_last_page(self):
        """Перейти на последнюю страницу."""
        offset = 0
        data, total_count = self.get_table_data(self.current_table, self.rows_per_page, offset)
        total_pages = (total_count + self.rows_per_page - 1) // self.rows_per_page if total_count > 0 else 1
        
        if total_pages > 0:
            self.current_page = total_pages - 1
            self.load_table_data()
    
    def on_page_changed(self, page):
        """Обработчик изменения страницы через спинбокс."""
        self.current_page = page - 1
        self.load_table_data()
    
    def on_rows_per_page_changed(self, rows):
        """Обработчик изменения количества строк на странице."""
        self.rows_per_page = rows
        self.current_page = 0
        self.load_table_data()
    
    def create_record(self):
        """Создать новую запись."""
        if not self.conn or not self.current_table:
            return
        
        try:
            values = {}
            for col_name, widget in self.create_fields.items():
                if isinstance(widget, QSpinBox):
                    values[col_name] = widget.value()
                elif isinstance(widget, QTextEdit):
                    values[col_name] = widget.toPlainText()
                else:
                    values[col_name] = widget.text()
            
            cursor = self.conn.cursor()
            columns = ", ".join(values.keys())
            placeholders = ", ".join(["?" for _ in values])
            query = f"INSERT INTO {self.current_table} ({columns}) VALUES ({placeholders})"
            cursor.execute(query, list(values.values()))
            self.conn.commit()
            
            QMessageBox.information(self, "Успех", "Запись успешно создана!")
            self.load_table_data()
            self.setup_crud_forms()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать запись:\n{e}")
    
    def on_edit_record_selected(self):
        """Обработчик выбора записи для редактирования."""
        self.open_edit_dialog_btn.setEnabled(self.edit_combo.currentIndex() >= 0)
    
    def open_edit_dialog(self):
        """Открыть диалог редактирования строки (OK/Cancel)."""
        if not self.conn or not self.current_table:
            return

        try:
            offset = self.current_page * self.rows_per_page
            data, _ = self.get_table_data(self.current_table, self.rows_per_page, offset)

            selected_idx = self.edit_combo.currentData()
            if selected_idx is None or selected_idx >= len(data):
                QMessageBox.warning(self, "Ошибка", "Выберите запись для редактирования")
                return

            selected_row = data[selected_idx]
            schema = self.get_table_schema(self.current_table)
            primary_key = self.get_primary_key_column(self.current_table)
            row_id = selected_row.get(primary_key) if primary_key else None

            if row_id is None:
                QMessageBox.warning(self, "Ошибка", "Не удалось определить ID записи")
                return

            dlg = RecordEditorDialog(
                parent=self,
                title="Редактировать строку",
                schema=schema,
                values=selected_row,
                primary_key=primary_key,
                dark_mode=self.dark_mode,
            )
            if dlg.exec_() != QDialog.Accepted:
                return

            values = dlg.get_values_for_update()
            if not values:
                return

            cursor = self.conn.cursor()
            set_clause = ", ".join([f"{key} = ?" for key in values.keys()])
            query = f"UPDATE {self.current_table} SET {set_clause} WHERE {primary_key} = ?"
            cursor.execute(query, list(values.values()) + [row_id])
            self.conn.commit()

            if cursor.rowcount > 0:
                QMessageBox.information(self, "Успех", "Запись успешно обновлена!")
                self.load_table_data()
                self.setup_crud_forms()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось обновить запись")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть редактирование:\n{e}")
    
    def on_delete_record_selected(self):
        """Обработчик выбора записи для удаления."""
        if self.delete_combo.currentIndex() < 0:
            return
        
        offset = self.current_page * self.rows_per_page
        data, _ = self.get_table_data(self.current_table, self.rows_per_page, offset)
        
        selected_idx = self.delete_combo.currentData()
        if selected_idx is not None and 0 <= selected_idx < len(data):
            selected_row = data[selected_idx]
            import json
            self.delete_info_text.setPlainText(json.dumps(dict(selected_row), indent=2, ensure_ascii=False))
    
    def delete_record(self):
        """Удалить запись."""
        if not self.conn or not self.current_table:
            return
        
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены, что хотите удалить эту запись?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            offset = self.current_page * self.rows_per_page
            data, _ = self.get_table_data(self.current_table, self.rows_per_page, offset)
            
            selected_idx = self.delete_combo.currentData()
            if selected_idx is None or selected_idx >= len(data):
                QMessageBox.warning(self, "Ошибка", "Выберите запись для удаления")
                return
            
            selected_row = data[selected_idx]
            primary_key = self.get_primary_key_column(self.current_table)
            row_id = selected_row.get(primary_key)
            
            if row_id is None:
                QMessageBox.warning(self, "Ошибка", "Не удалось определить ID записи")
                return
            
            cursor = self.conn.cursor()
            query = f"DELETE FROM {self.current_table} WHERE {primary_key} = ?"
            cursor.execute(query, (row_id,))
            self.conn.commit()
            
            if cursor.rowcount > 0:
                QMessageBox.information(self, "Успех", "Запись успешно удалена!")
                self.load_table_data()
                self.setup_crud_forms()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось удалить запись")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось удалить запись:\n{e}")
    
    def toggle_theme(self):
        """Переключить тему между светлой и темной."""
        self.dark_mode = not self.dark_mode
        self.apply_theme()
    
    def apply_theme(self):
        """Применить текущую тему к интерфейсу."""
        if self.dark_mode:
            # Темная тема
            self.theme_btn.setText("☀️")
            # Применяем темную тему к заголовку окна
            self.apply_window_theme(True)
            dark_stylesheet = """
                QMainWindow {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QWidget {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QGroupBox {
                    border: 2px solid #555555;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                    font-weight: bold;
                    color: #ffffff;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
                QPushButton {
                    background-color: #404040;
                    color: #ffffff;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 5px 15px;
                    min-height: 25px;
                }
                QPushButton:hover {
                    background-color: #505050;
                }
                QPushButton:pressed {
                    background-color: #303030;
                }
                QPushButton:disabled {
                    background-color: #2b2b2b;
                    color: #666666;
                    border: 1px solid #404040;
                }
                QLabel {
                    color: #ffffff;
                }
                QLineEdit, QTextEdit {
                    background-color: #3c3c3c;
                    color: #ffffff;
                    border: 1px solid #555555;
                    border-radius: 3px;
                    padding: 5px;
                }
                QLineEdit:focus, QTextEdit:focus {
                    border: 2px solid #0078d4;
                }
                QComboBox {
                    background-color: #3c3c3c;
                    color: #ffffff;
                    border: 1px solid #555555;
                    border-radius: 3px;
                    padding: 5px;
                    min-width: 150px;
                }
                QComboBox:hover {
                    background-color: #404040;
                }
                QComboBox::drop-down {
                    border: none;
                }
                QComboBox::down-arrow {
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 5px solid #ffffff;
                    margin-right: 5px;
                }
                QComboBox QAbstractItemView {
                    background-color: #3c3c3c;
                    color: #ffffff;
                    selection-background-color: #0078d4;
                    selection-color: #ffffff;
                    border: 1px solid #555555;
                }
                QTableWidget {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    gridline-color: #555555;
                    border: 1px solid #555555;
                }
                QTableWidget::item {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QTableWidget::item:selected {
                    background-color: #0078d4;
                    color: #ffffff;
                }
                QTableWidget::item:selected:active {
                    background-color: #0078d4;
                    color: #ffffff;
                }
                QTableWidget::item:focus {
                    outline: none;
                }
                QHeaderView::section {
                    background-color: #404040;
                    color: #ffffff;
                    padding: 5px;
                    border: 1px solid #555555;
                    font-weight: bold;
                }
                QTabWidget::pane {
                    border: 1px solid #555555;
                    background-color: #2b2b2b;
                }
                QTabBar::tab {
                    background-color: #404040;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 8px 20px;
                    margin-right: 2px;
                }
                QTabBar::tab:selected {
                    background-color: #0078d4;
                    color: #ffffff;
                }
                QTabBar::tab:hover {
                    background-color: #505050;
                }
                QSpinBox {
                    background-color: #3c3c3c;
                    color: #ffffff;
                    border: 1px solid #555555;
                    border-radius: 3px;
                    padding: 5px;
                }
                QSpinBox:hover {
                    background-color: #404040;
                }
                QSpinBox::up-button, QSpinBox::down-button {
                    background-color: #404040;
                    border: 1px solid #555555;
                    width: 20px;
                }
                QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                    background-color: #505050;
                }
                QSpinBox::up-arrow, QSpinBox::down-arrow {
                    width: 0;
                    height: 0;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                }
                QSpinBox::up-arrow {
                    border-bottom: 4px solid #ffffff;
                }
                QSpinBox::down-arrow {
                    border-top: 4px solid #ffffff;
                }
                QToolBar {
                    background-color: #1e1e1e;
                    border: none;
                    border-bottom: 1px solid #555555;
                }
                QMenuBar {
                    background-color: #1e1e1e;
                    color: #ffffff;
                    border: none;
                    border-bottom: 1px solid #555555;
                }
                QMenuBar::item {
                    background-color: #1e1e1e;
                    color: #ffffff;
                    padding: 5px 10px;
                }
                QMenuBar::item:selected {
                    background-color: #404040;
                }
                QMenu {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    border: 1px solid #555555;
                }
                QMenu::item {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    padding: 5px 30px;
                }
                QMenu::item:selected {
                    background-color: #404040;
                }
                QStatusBar {
                    background-color: #1e1e1e;
                    color: #ffffff;
                    border-top: 1px solid #555555;
                }
            """
            self.setStyleSheet(dark_stylesheet)
            # Применяем темную тему к тулбару
            for toolbar in self.findChildren(QToolBar):
                toolbar.setStyleSheet("background-color: #1e1e1e; border: none; border-bottom: 1px solid #555555;")
            # Обновляем стиль для file_label
            self.file_label.setStyleSheet("color: #ffffff;")
        else:
            # Светлая тема (стандартная)
            self.theme_btn.setText("🌙")
            # Возвращаем светлую тему для заголовка окна
            self.apply_window_theme(False)
            # Стили для светлой темы с выделением целых строк
            light_stylesheet = """
                QTableWidget::item:selected {
                    background-color: #0078d4;
                    color: #ffffff;
                }
                QTableWidget::item:selected:active {
                    background-color: #0078d4;
                    color: #ffffff;
                }
                QTableWidget::item:focus {
                    outline: none;
                }
            """
            self.setStyleSheet(light_stylesheet)
            # Обновляем стиль для file_label
            if self.db_path:
                self.file_label.setStyleSheet("color: black;")
            else:
                self.file_label.setStyleSheet("color: gray;")
    
    def eventFilter(self, obj, event):
        """Обработчик событий для снятия выделения при клике по пустому месту."""
        if obj == self.table_widget.viewport() and event.type() == QEvent.MouseButtonPress:
            # Проверяем, что клик был не по ячейке
            item = self.table_widget.itemAt(event.pos())
            if item is None:
                # Клик по пустому месту в таблице - снимаем выделение
                self.table_widget.clearSelection()
                return True
        return super().eventFilter(obj, event)
    
    def on_central_widget_clicked(self, event):
        """Обработчик клика по центральному виджету для снятия выделения."""
        # Если клик был не по таблице, снимаем выделение
        if self.table_widget and event.button() == Qt.LeftButton:
            # Проверяем, что клик был не по таблице
            table_rect = self.table_widget.geometry()
            if not table_rect.contains(event.pos()):
                self.table_widget.clearSelection()
    
    def closeEvent(self, event):
        """Обработчик закрытия окна."""
        if self.conn:
            self.conn.close()
        event.accept()


def main():
    """Главная функция запуска приложения."""
    app = QApplication(sys.argv)
    window = DatabaseViewer()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
