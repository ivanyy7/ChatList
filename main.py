import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtGui import QFont


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Минимальное PyQt приложение")
        self.setGeometry(100, 100, 600, 450)
        
        # Создаем центральный виджет и layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Добавляем метку
        self.label = QLabel("Привет, PyQt!")
        self.label.setStyleSheet("font-size: 18px; padding: 20px;")
        layout.addWidget(self.label)
        
        # Флаг для отслеживания состояния
        self.is_first_click = True
        
        # Добавляем кнопку
        self.button = QPushButton("Нажми меня")
        font = QFont()
        font.setPointSize(font.pointSize() + 10)
        self.button.setFont(font)
        self.button.clicked.connect(self.on_button_clicked)
        layout.addWidget(self.button)
    
    def on_button_clicked(self):
        if self.is_first_click:
            self.label.setText("Минимальная программа на Python!")
            self.is_first_click = False
        else:
            self.label.setText("Привет, PyQt!")
            self.is_first_click = True


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
