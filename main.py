import sys
import logging
import locale
from PyQt5.QtWidgets import QApplication,QMessageBox, QDialog
from ui.main_window import MainWindow
from utils.helpers import setup_logging, get_config
from utils.notifications import setup_notifications
from database.db import init_db
from PyQt5.QtCore import QTextCodec
from logging.handlers import RotatingFileHandler
from core.auth import AuthManager
from ui.dialogs import LoginDialog

# Устанавливаем UTF-8 как стандартную кодировку
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')

# Устанавливаем UTF-8 как кодировку по умолчанию для PyQt5
QTextCodec.setCodecForLocale(QTextCodec.codecForName("UTF-8"))

def setup_logging():
    """Настройка логирования"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler(
                'equipment_manager.log', maxBytes=1024*1024, backupCount=5
            ),
            logging.StreamHandler()
        ]
    )

def main():
    # Инициализация базы данных
    init_db()

    # Создание приложения PyQt5
    app = QApplication(sys.argv)

    # Создание менеджера авторизации
    auth_manager = AuthManager()

    # Показываем окно авторизации
    login_dialog = LoginDialog(auth_manager)
    if login_dialog.exec_() != QDialog.Accepted:
        sys.exit()  # Выход, если авторизация не прошла

    # Получаем данные пользователя
    user = login_dialog.get_user()
    if not user:
        QMessageBox.critical(None, "Ошибка", "Не удалось получить данные пользователя")
        sys.exit()

    # Применение стилей
    try:
        with open("ui/styles.qss", "r") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        logging.warning("Stylesheet not found, using default styles")

    # Создание и отображение главного окна с данными пользователя
    window = MainWindow(user)
    window.show()

    # Запуск основного цикла приложения
    sys.exit(app.exec_())



if __name__ == "__main__":
    main()