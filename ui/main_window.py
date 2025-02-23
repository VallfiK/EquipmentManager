# ui/main_window.py
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, 
                            QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
                            QDateEdit, QComboBox, QLabel, QMessageBox, QTableWidget,
                            QTableWidgetItem, QHeaderView, QMenu, QAction)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QIcon
from core.equipment import EquipmentManager
from core.auth import AuthManager
from core.reports import ReportGenerator
from database.db import db_connection
from .dialogs import EquipmentDialog, UserDialog, LoginDialog
import webbrowser
from utils.helpers import show_error_message, show_info_message
from PyQt5.QtWidgets import QInputDialog
from .dialogs import UserDialog
from utils.helpers import convert_cp1251_to_utf8
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import logging

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.report_generator = ReportGenerator()
        self.equipment_manager = EquipmentManager()
        self.auth_manager = AuthManager()
        self.init_ui()  # Инициализация интерфейса
        self.setWindowTitle(f"Учет оборудования - {user['username']}")
        self.setMinimumSize(1024, 768)
        self.load_data()  # Загрузка данных оборудования
        self.load_users_data()  # Загрузка данных пользователей
        self.update_ui_for_role()  # Обновление интерфейса для роли

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Вкладка оборудования
        self.equipment_tab = QWidget()
        self.init_equipment_tab()
        self.tabs.addTab(self.equipment_tab, "Оборудование")

        # Вкладка отчетов
        self.reports_tab = QWidget()
        self.init_reports_tab()
        self.tabs.addTab(self.reports_tab, "Отчеты")

        # Вкладка пользователей (только для админов)
        self.users_tab = QWidget()
        self.init_users_tab()  # Инициализация вкладки пользователей
        self.tabs.addTab(self.users_tab, "Пользователи")

        # Статус бар
        self.statusBar().showMessage("Готово")

        # Меню
        self.init_menu()

    def init_equipment_tab(self):
        """Инициализация вкладки оборудования"""
        layout = QVBoxLayout()

        # Панель инструментов
        toolbar = QHBoxLayout()
        
        self.add_button = QPushButton("Добавить")
        self.add_button.clicked.connect(self.add_equipment)
        toolbar.addWidget(self.add_button)

        self.edit_button = QPushButton("Редактировать")
        self.edit_button.clicked.connect(self.edit_equipment)
        toolbar.addWidget(self.edit_button)

        self.delete_button = QPushButton("Удалить")
        self.delete_button.clicked.connect(self.delete_equipment)
        toolbar.addWidget(self.delete_button)

        # Фильтры
        toolbar.addWidget(QLabel("Фильтры:"))

        # Добавьте кнопку сброса фильтров
        self.reset_filters_btn = QPushButton("Сбросить фильтры")
        self.reset_filters_btn.clicked.connect(self.reset_filters)
        toolbar.addWidget(self.reset_filters_btn)
        
        self.category_filter = QComboBox()
        self.category_filter.addItem("Все категории", None)
        self.load_categories()
        self.category_filter.currentIndexChanged.connect(self.apply_filters)
        toolbar.addWidget(self.category_filter)

        self.status_filter = QComboBox()
        self.status_filter.addItem("Все статусы", None)
        self.status_filter.addItems(self.equipment_manager.status_options)
        self.status_filter.currentIndexChanged.connect(self.apply_filters)
        toolbar.addWidget(self.status_filter)

        layout.addLayout(toolbar)

        # Таблица оборудования
        self.equipment_table = QTableWidget()
        self.equipment_table.setColumnCount(6)
        self.equipment_table.setHorizontalHeaderLabels([
            "ID", "Наименование", "Категория", "Серийный номер", "Статус", "Дата ТО"
        ])
        self.equipment_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.equipment_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.equipment_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.equipment_table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.equipment_table)

        self.equipment_tab.setLayout(layout)

    def reset_filters(self):
        """Сброс всех фильтров"""
        self.category_filter.setCurrentIndex(0)
        self.status_filter.setCurrentIndex(0)
        self.apply_filters()

    def init_reports_tab(self):
        """Инициализация вкладки отчетов"""
        layout = QVBoxLayout()
        
        # Список кнопок и их обработчиков
        report_buttons = [
            ("Список оборудования (PDF)", self.generate_equipment_list_pdf),
            ("Оборудование с истекающим ТО (Excel)", self.generate_service_due_excel),
            ("Полный инвентаризационный отчет (PDF)", self.generate_full_inventory_report)
        ]
        
        # Создание кнопок
        for text, handler in report_buttons:
            btn = QPushButton(text)
            btn.clicked.connect(handler)  # Исправлено: передаем handler напрямую
            layout.addWidget(btn)
        
        self.reports_tab.setLayout(layout)

    def show_error_message(self, title, message):
        QMessageBox.critical(self, title, message)

    def show_info_message(self, title, message):
        QMessageBox.information(self, title, message)

    def init_users_tab(self):
        """Инициализация вкладки пользователей"""
        layout = QVBoxLayout()

        # Таблица пользователей
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(4)
        self.users_table.setHorizontalHeaderLabels([
            "ID", "Логин", "Роль", "Дата регистрации"
        ])
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.users_table)

        # Кнопки управления
        btn_layout = QHBoxLayout()
        
        self.add_user_btn = QPushButton("Добавить пользователя")
        self.add_user_btn.clicked.connect(self.add_user)
        btn_layout.addWidget(self.add_user_btn)

        self.edit_user_btn = QPushButton("Изменить роль")
        self.edit_user_btn.clicked.connect(self.edit_user_role)
        btn_layout.addWidget(self.edit_user_btn)

        self.delete_user_btn = QPushButton("Удалить пользователя")
        self.delete_user_btn.clicked.connect(self.delete_user)
        btn_layout.addWidget(self.delete_user_btn)

        layout.addLayout(btn_layout)
        self.users_tab.setLayout(layout)

        # Загрузка данных пользователей
        self.load_users_data()

    def load_users_data(self):
        """Загрузка данных в таблицу пользователей"""
        try:
            if not hasattr(self, 'users_table'):
                return

            # Проверка прав доступа
            if not self.user or self.user['role'] != 'admin':
                self.users_table.setRowCount(0)
                return

            # Очистка таблицы
            self.users_table.setRowCount(0)

            # Получение списка пользователей
            users = self.auth_manager.list_users()
            
            # Заполнение таблицы
            for row_idx, user in enumerate(users):
                self.users_table.insertRow(row_idx)
                self.users_table.setItem(row_idx, 0, QTableWidgetItem(str(user['id'])))
                self.users_table.setItem(row_idx, 1, QTableWidgetItem(user['username']))
                self.users_table.setItem(row_idx, 2, QTableWidgetItem(user['role']))
                self.users_table.setItem(row_idx, 3, QTableWidgetItem(user['created_at']))
                
        except Exception as e:
            logger.error(f"Ошибка загрузки пользователей: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить пользователей: {e}")

    def generate_equipment_list_pdf(self):
        """Генерация PDF-отчета со списком оборудования"""
        try:
            # Регистрация шрифта с поддержкой кириллицы
            pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
            
            # Создание PDF-документа
            report_path = "equipment_list.pdf"
            c = canvas.Canvas(report_path)
            
            # Установка шрифта
            c.setFont("DejaVuSans", 12)
            
            # Заголовок
            c.drawString(250, 750, "Список оборудования")
            
            # Получение данных
            equipment_list = self.equipment_manager.search_equipment({})
            
            # Позиция для текста
            y_position = 700
            # Запись данных
            for equipment in equipment_list:
                c.drawString(50, y_position, f"ID: {equipment['id']}")
                c.drawString(150, y_position, f"Наименование: {equipment['name']}")
                c.drawString(350, y_position, f"Серийный номер: {equipment['serial_number']}")
                y_position -= 20  # Смещение для следующей строки
            
            # Сохранение PDF
            c.save()
            
            return report_path
        except Exception as e:
            logger.error(f"Ошибка генерации PDF: {e}")
            raise

    def generate_service_due_excel(self):
        """Генерация Excel-отчета по ТО"""
        try:
            report_path = self.report_generator.generate_service_due_excel()
            self.show_info_message("Успех", f"Отчет сохранен: {report_path}")
            webbrowser.open(report_path)
        except Exception as e:
            self.show_error_message("Ошибка", f"Не удалось создать отчет: {str(e)}")

    def generate_full_inventory_report(self):
        """Генерация полного инвентаризационного отчета"""
        try:
            report_path = self.report_generator.generate_full_inventory_report()
            self.show_info_message("Успех", f"Отчет сохранен: {report_path}")
            webbrowser.open(report_path)
        except Exception as e:
            self.show_error_message("Ошибка", f"Не удалось создать отчет: {str(e)}")

    def init_menu(self):
        """Инициализация главного меню"""
        menubar = self.menuBar()

        # Меню Файл
        file_menu = menubar.addMenu("Файл")

        logout_action = QAction("Выйти", self)
        logout_action.triggered.connect(self.logout)
        file_menu.addAction(logout_action)

        exit_action = QAction("Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Меню Справка
        help_menu = menubar.addMenu("Справка")

        about_action = QAction("О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        docs_action = QAction("Документация", self)
        docs_action.triggered.connect(lambda: webbrowser.open("https://example.com/docs"))
        help_menu.addAction(docs_action)

    def load_data(self):
        """Загрузка данных в таблицу оборудования"""
        try:
            self.equipment_table.setRowCount(0)
            equipment_list = self.equipment_manager.search_equipment({})
            
            for row_idx, item in enumerate(equipment_list):
                self.equipment_table.insertRow(row_idx)
                
                # Явное указание порядка столбцов
                self.equipment_table.setItem(row_idx, 0, QTableWidgetItem(str(item['id'])))
                self.equipment_table.setItem(row_idx, 1, QTableWidgetItem(item['name']))
                self.equipment_table.setItem(row_idx, 2, QTableWidgetItem(item['category']))
                self.equipment_table.setItem(row_idx, 3, QTableWidgetItem(item['serial_number']))
                self.equipment_table.setItem(row_idx, 4, QTableWidgetItem(item['status']))
                self.equipment_table.setItem(row_idx, 5, QTableWidgetItem(item['next_service']))
                
        except Exception as e:
            logger.error(f"Ошибка при загрузке данных: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить данные: {e}")

    def add_user(self):
        """Добавление нового пользователя"""
        dialog = UserDialog(self, current_user_role=self.user['role'])  # Передаем роль текущего пользователя
        if dialog.exec_():
            try:
                user_data = dialog.get_data()
                self.auth_manager.create_user(
                    username=user_data['username'],
                    password=user_data['password'],
                    role=user_data['role'],
                    creator_role=self.user['role']  # Передаем роль создателя
                )
                self.load_users_data()  # Обновляем список пользователей
                self.statusBar().showMessage("Пользователь добавлен", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))

    def edit_user_role(self):
        """Изменение роли пользователя"""
        selected_row = self.users_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите пользователя")
            return

        user_id = int(self.users_table.item(selected_row, 0).text())
        new_role, ok = QInputDialog.getItem(
            self,
            "Изменение роли",
            "Выберите новую роль:",
            ["admin", "user"],
            0,
            False
        )
        
        if ok and new_role:
            try:
                self.auth_manager.update_user_role(user_id, new_role)
                self.load_data()
                self.statusBar().showMessage("Роль обновлена", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))

    def delete_user(self):
        """Удаление пользователя"""
        selected_row = self.users_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите пользователя")
            return

        user_id = int(self.users_table.item(selected_row, 0).text())
        
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите удалить этого пользователя?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if self.auth_manager.delete_user(user_id):
                    self.load_data()
                    self.statusBar().showMessage("Пользователь удален", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))

    def load_categories(self):
        """Загрузка категорий в выпадающий список"""
        try:
            self.category_filter.clear()
            self.category_filter.addItem("Все категории", None)
            
            with db_connection() as conn:
                cursor = conn.execute("SELECT id, name FROM categories ORDER BY name")
                for category in cursor.fetchall():
                    self.category_filter.addItem(
                        category['name'],  # Убрано конвертирование кодировки
                        category['id']
                    )
                    
        except Exception as e:
            logger.error(f"Ошибка при загрузке категорий: {e}")

    def apply_filters(self):
        """Применение фильтров к таблице оборудования"""
        try:
            filters = {
                'category_id': self.category_filter.currentData(),
                'status': self.status_filter.currentText() if self.status_filter.currentIndex() > 0 else None
            }
            
            equipment = self.equipment_manager.search_equipment(filters)
            
            self.equipment_table.setRowCount(0)
            
            for row_idx, item in enumerate(equipment):
                self.equipment_table.insertRow(row_idx)
                self.equipment_table.setItem(row_idx, 0, QTableWidgetItem(str(item['id'])))
                self.equipment_table.setItem(row_idx, 1, QTableWidgetItem(item['name']))
                self.equipment_table.setItem(row_idx, 2, QTableWidgetItem(item['category']))
                self.equipment_table.setItem(row_idx, 3, QTableWidgetItem(item['serial_number']))
                self.equipment_table.setItem(row_idx, 4, QTableWidgetItem(item['status']))
                self.equipment_table.setItem(row_idx, 5, QTableWidgetItem(item['next_service']))
                    
        except Exception as e:
            logger.error(f"Ошибка фильтрации: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка применения фильтров: {str(e)}")

    def show_context_menu(self, position):
        """Контекстное меню для таблицы оборудования"""
        if not self.user:  # Исправлено: используем self.user
            return
        
        menu = QMenu()
        edit_action = QAction("Редактировать", self)
        edit_action.triggered.connect(self.edit_equipment)
        menu.addAction(edit_action)

        delete_action = QAction("Удалить", self)
        delete_action.triggered.connect(self.delete_equipment)
        menu.addAction(delete_action)

        menu.exec_(self.equipment_table.viewport().mapToGlobal(position))

    def add_equipment(self):
        """Добавление нового оборудования"""
        if not self.user:
            QMessageBox.warning(self, "Ошибка", "Необходимо авторизоваться для выполнения этой операции")
            return
        
        logger.debug("Открытие диалога добавления оборудования")
        dialog = EquipmentDialog(self)
        if dialog.exec_():
            try:
                equipment_data = dialog.get_data()
                logger.debug(f"Данные для добавления: {equipment_data}")
                
                if not equipment_data['category_id']:
                    logger.error("Категория не выбрана")
                    raise ValueError("Категория не выбрана")
                    
                logger.debug("Добавление оборудования в базу данных")
                self.equipment_manager.add_equipment(equipment_data, self.user['id'])  # Передаем user_id
                
                logger.debug("Обновление таблицы оборудования")
                self.load_data()
                
                logger.info("Оборудование успешно добавлено")
                self.statusBar().showMessage("Оборудование добавлено", 3000)
                
            except Exception as e:
                logger.error(f"Ошибка при добавлении оборудования: {e}")
                QMessageBox.critical(self, "Ошибка", str(e))

    def edit_equipment(self):
        """Редактирование выбранного оборудования"""
        if not self.user:  # Change from self.current_user to self.user
            QMessageBox.warning(self, "Ошибка", "Необходимо авторизоваться для выполнения этой операции")
            return
        
        selected_row = self.equipment_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите оборудование для редактирования")
            return

        equipment_id = int(self.equipment_table.item(selected_row, 0).text())
        dialog = EquipmentDialog(self, equipment_id)
        if dialog.exec_():
            try:
                update_data = dialog.get_data()
                self.equipment_manager.update_equipment(
                    equipment_id, 
                    update_data, 
                    self.user['id']  # Change from self.current_user to self.user
                )
                self.load_data()
                self.statusBar().showMessage("Оборудование успешно обновлено", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))

    def delete_equipment(self):
        """Удаление выбранного оборудования"""
        if not self.user:  # Change from self.current_user to self.user
            QMessageBox.warning(self, "Ошибка", "Необходимо авторизоваться для выполнения этой операции")
            return
        
        selected_row = self.equipment_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите оборудование для удаления")
            return

        equipment_id = int(self.equipment_table.item(selected_row, 0).text())
        
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите удалить это оборудование?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if self.equipment_manager.delete_equipment(equipment_id, self.user['id']):  # Change from self.current_user to self.user
                    self.load_data()
                    self.statusBar().showMessage("Оборудование удалено", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))

    def show_about(self):
        """Окно 'О программе'"""
        QMessageBox.about(self, "О программе",
            "Программа учета оборудования\n"
            "Версия 1.0\n\n"
            "© 2024 Ваше имя/компания")

    def login(self):
        """Авторизация пользователя"""
        while not self.user:  # Change from self.current_user to self.user
            dialog = LoginDialog(self)
            if dialog.exec_():
                username = dialog.username()
                password = dialog.password()
                
                user = self.auth_manager.authenticate(username, password)
                if user:
                    self.user = user  # Change from self.current_user to self.user
                    self.setWindowTitle(f"Учет оборудования - {user['username']}")
                    self.update_ui_for_role()
                    self.load_data()
                else:
                    QMessageBox.warning(self, "Ошибка", "Неверный логин или пароль")
            else:
                self.close()  # Закрываем окно, если пользователь отменил авторизацию
                return

    def logout(self):
        """Выход из системы"""
        self.user = None  # Change from self.current_user to self.user
        self.setWindowTitle("Учет оборудования")
        self.update_ui_for_role()
        self.login()  # Показываем окно авторизации

    def update_ui_for_role(self):
        """Обновление интерфейса для роли"""
        is_admin = self.user and self.user['role'] == 'admin'
        
        # Вкладка пользователей
        self.tabs.setTabEnabled(2, is_admin)
        
        # Кнопки управления
        self.add_user_btn.setVisible(is_admin)
        self.edit_user_btn.setVisible(is_admin)
        self.delete_user_btn.setVisible(is_admin)
        
        # Обновление данных
        if is_admin:
            self.load_users_data()

def main():
    app = QApplication(sys.argv)
    
    # Загрузка стилей
    with open("ui/styles.qss", "r") as f:
        app.setStyleSheet(f.read())
    
    window = MainWindow()
    window.login()  # Показываем окно авторизации
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()