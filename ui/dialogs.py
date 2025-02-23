# ui/dialogs.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                            QLineEdit, QComboBox, QDateEdit, QPushButton, 
                            QLabel, QMessageBox, QDialogButtonBox)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QIntValidator
from database.db import db_connection
from utils.helpers import convert_cp1251_to_utf8
import logging

logger = logging.getLogger(__name__)

class EquipmentDialog(QDialog):
    """Диалоговое окно для добавления/редактирования оборудования"""
    def __init__(self, parent=None, equipment_id=None):
        super().__init__(parent)
        self.equipment_id = equipment_id
        self.init_ui()
        self.setWindowTitle("Добавить оборудование" if not equipment_id else "Редактировать оборудование")
        self.setMinimumWidth(400)
        
        if equipment_id:
            self.load_data()

    def init_ui(self):
        layout = QVBoxLayout()

        # Форма ввода данных
        form = QFormLayout()
        
        self.name_input = QLineEdit()
        form.addRow("Наименование:", self.name_input)
        
        self.category_input = QComboBox()
        self.load_categories()
        form.addRow("Категория:", self.category_input)
        
        self.serial_input = QLineEdit()
        form.addRow("Серийный номер:", self.serial_input)
        
        self.status_input = QComboBox()
        self.status_input.addItems(["В работе", "На ремонте", "Списано"])
        form.addRow("Статус:", self.status_input)
        
        self.purchase_date_input = QDateEdit()
        self.purchase_date_input.setCalendarPopup(True)
        self.purchase_date_input.setDate(QDate.currentDate())
        form.addRow("Дата приобретения:", self.purchase_date_input)
        
        self.price_input = QLineEdit()
        self.price_input.setValidator(QIntValidator())
        form.addRow("Стоимость:", self.price_input)
        
        self.next_service_input = QDateEdit()
        self.next_service_input.setCalendarPopup(True)
        self.next_service_input.setDate(QDate.currentDate().addMonths(6))
        form.addRow("Дата следующего ТО:", self.next_service_input)
        
        self.notes_input = QLineEdit()
        form.addRow("Примечания:", self.notes_input)
        
        layout.addLayout(form)

        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    
    def load_categories(self):
        """Загрузка категорий в выпадающий список"""
        self.category_input.clear()
        
        try:
            with db_connection() as conn:
                cursor = conn.execute("SELECT id, name FROM categories ORDER BY name")
                for category in cursor.fetchall():
                    name_utf8 = convert_cp1251_to_utf8(category['name'])
                    self.category_input.addItem(name_utf8, category['id'])
                    
            if self.category_input.count() == 0:
                raise ValueError("Категории не найдены в базе данных")
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def load_data(self):
        """Загрузка данных оборудования для редактирования"""
        with db_connection() as conn:
            equipment = conn.execute('''
                SELECT * FROM equipment WHERE id = ?
            ''', (self.equipment_id,)).fetchone()
            
            if equipment:
                self.name_input.setText(equipment['name'])
                self.category_input.setCurrentIndex(
                    self.category_input.findData(equipment['category_id']))
                self.serial_input.setText(equipment['serial_number'])
                self.status_input.setCurrentText(equipment['status'])
                self.purchase_date_input.setDate(QDate.fromString(equipment['purchase_date'], 'yyyy-MM-dd'))
                self.price_input.setText(str(equipment['purchase_price'] or ''))
                if equipment['next_service']:
                    self.next_service_input.setDate(QDate.fromString(equipment['next_service'], 'yyyy-MM-dd'))
                self.notes_input.setText(equipment['notes'] or '')

    def get_data(self):
        """Получение данных из формы"""
        return {
            'name': self.name_input.text().strip(),
            'category_id': self.category_input.currentData(),
            'serial_number': self.serial_input.text().strip(),
            'status': self.status_input.currentText(),
            'purchase_date': self.purchase_date_input.date().toString('yyyy-MM-dd'),
            'purchase_price': int(float(self.price_input.text())) if self.price_input.text() else None,  # Исправлено
            'next_service': self.next_service_input.date().toString('yyyy-MM-dd'),
            'notes': self.notes_input.text().strip(),
        }

    def validate_and_accept(self):
        """Валидация данных перед сохранением"""
        data = self.get_data()
        
        if not data['name']:
            QMessageBox.warning(self, "Ошибка", "Укажите наименование оборудования")
            return
            
        if not data['category_id']:
            QMessageBox.warning(self, "Ошибка", "Выберите категорию")
            return
            
        if not data['serial_number']:
            QMessageBox.warning(self, "Ошибка", "Укажите серийный номер")
            return
            
        self.accept()

class LoginDialog(QDialog):
    """Диалоговое окно авторизации"""
    def __init__(self, auth_manager, parent=None):
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.user = None  # Добавляем атрибут для хранения данных пользователя
        self.init_ui()
        self.setWindowTitle("Авторизация")
        self.user = None
        self.setFixedSize(300, 150)

    def init_ui(self):
        layout = QVBoxLayout()

        form = QFormLayout()
        
        self.username_input = QLineEdit()
        form.addRow("Логин:", self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        form.addRow("Пароль:", self.password_input)
        
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self.authenticate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def authenticate(self):
        """Проверка учетных данных"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        user = self.auth_manager.authenticate(username, password)
        if user:
            self.user = user  # Сохраняем данные пользователя
            self.accept()  # Закрываем диалог с результатом Accepted
        else:
            QMessageBox.warning(self, "Ошибка", "Неверный логин или пароль")
            
    def username(self):
        return self.username_input.text().strip()

    def password(self):
        return self.password_input.text().strip()
    
    def get_user(self):
        """Возвращает данные пользователя"""
        return self.user

class UserDialog(QDialog):
    """Диалоговое окно для добавления/редактирования пользователей"""
    def __init__(self, parent=None, user_id=None, current_user_role=None):
        super().__init__(parent)
        self.current_user_role = current_user_role  # Роль текущего пользователя
        self.user_id = user_id  # ID редактируемого пользователя (если есть)
        self.init_ui()
        self.setWindowTitle("Добавить пользователя" if not user_id else "Редактировать пользователя")
        self.setMinimumWidth(300)
        
        if user_id:
            self.load_data()

    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout()

        # Форма ввода данных
        form = QFormLayout()
        
        # Поле для логина
        self.username_input = QLineEdit()
        form.addRow("Логин:", self.username_input)
        
        # Поле для пароля
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        form.addRow("Пароль:", self.password_input)
        
        # Выбор роли
        self.role_input = QComboBox()
        
        # Если текущий пользователь не админ, ограничиваем выбор роли
        if self.current_user_role != "admin":
            self.role_input.setEnabled(False)  # Блокируем выбор
            self.role_input.addItem("user")    # Только роль "user"
        else:
            self.role_input.addItems(["admin", "user"])  # Все роли для админа
        
        form.addRow("Роль:", self.role_input)
        
        layout.addLayout(form)

        # Кнопки управления
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def load_data(self):
        """Загрузка данных пользователя для редактирования"""
        with db_connection() as conn:
            user = conn.execute('''
                SELECT username, role FROM users WHERE id = ?
            ''', (self.user_id,)).fetchone()
            
            if user:
                self.username_input.setText(user['username'])
                self.role_input.setCurrentText(user['role'])

    def get_data(self):
        """Получение данных из формы"""
        return {
            'username': self.username_input.text().strip(),
            'password': self.password_input.text().strip(),
            'role': self.role_input.currentText()
        }

    def validate_and_accept(self):
        """Валидация данных перед сохранением"""
        data = self.get_data()
        
        # Проверка логина
        if not data['username']:
            QMessageBox.warning(self, "Ошибка", "Укажите логин пользователя")
            return
            
        # Проверка пароля
        if not data['password']:
            QMessageBox.warning(self, "Ошибка", "Укажите пароль")
            return
            
        # Проверка длины пароля
        if len(data['password']) < 8:
            QMessageBox.warning(self, "Ошибка", "Пароль должен содержать не менее 8 символов")
            return
            
        # Если текущий пользователь не админ, запрещаем создание администраторов
        if self.current_user_role != "admin" and data['role'] == "admin":
            QMessageBox.warning(self, "Ошибка", "Обычные пользователи не могут создавать администраторов")
            return
            
        self.accept()