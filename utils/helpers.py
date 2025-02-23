# utils/helpers.py
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import sqlite3
from PyQt5.QtWidgets import QMessageBox

def validate_date(date_str: str, fmt: str = '%Y-%m-%d') -> bool:
    """
    Проверка корректности даты в строковом формате
    :param date_str: Строка с датой
    :param fmt: Формат даты
    :return: True если дата корректна
    """
    try:
        datetime.strptime(date_str, fmt)
        return True
    except ValueError:
        return False

def format_date(date_str: str, 
                from_fmt: str = '%Y-%m-%d', 
                to_fmt: str = '%d.%m.%Y') -> Optional[str]:
    """
    Форматирование даты из одного формата в другой
    :param date_str: Исходная строка с датой
    :param from_fmt: Исходный формат
    :param to_fmt: Целевой формат
    :return: Отформатированная строка или None
    """
    try:
        date_obj = datetime.strptime(date_str, from_fmt)
        return date_obj.strftime(to_fmt)
    except (ValueError, TypeError):
        return None

def calculate_next_service(last_service: str, 
                          interval_days: int = 180) -> Optional[str]:
    """
    Расчет даты следующего ТО
    :param last_service: Дата последнего ТО в формате 'YYYY-MM-DD'
    :param interval_days: Интервал в днях
    :return: Дата следующего ТО в формате 'YYYY-MM-DD' или None
    """
    if not validate_date(last_service):
        return None
        
    try:
        next_service = (datetime.strptime(last_service, '%Y-%m-%d') + 
                       timedelta(days=interval_days))
        return next_service.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return None

def backup_database(db_path: str, backup_dir: str = "backups") -> Optional[str]:
    """
    Создание резервной копии базы данных
    :param db_path: Путь к основной базе данных
    :param backup_dir: Директория для резервных копий
    :return: Путь к созданной копии или None
    """
    try:
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f"backup_{timestamp}.db")
        
        with sqlite3.connect(db_path) as src:
            with sqlite3.connect(backup_path) as dst:
                src.backup(dst)
                
        return backup_path
    except Exception as e:
        print(f"Backup failed: {e}")
        return None

def show_error_message(parent, title: str, message: str):
    """
    Показать сообщение об ошибке
    :param parent: Родительское окно
    :param title: Заголовок окна
    :param message: Текст сообщения
    """
    QMessageBox.critical(parent, title, message)

def show_info_message(parent, title: str, message: str):
    """
    Показать информационное сообщение
    :param parent: Родительское окно
    :param title: Заголовок окна
    :param message: Текст сообщения
    """
    QMessageBox.information(parent, title, message)

def dict_factory(cursor, row) -> Dict:
    """
    Фабрика для преобразования строки SQLite в словарь
    :param cursor: Курсор базы данных
    :param row: Строка результата
    :return: Словарь с данными
    """
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}

def export_to_json(data: List[Dict], file_path: str) -> bool:
    """
    Экспорт данных в JSON файл
    :param data: Список словарей с данными
    :param file_path: Путь для сохранения файла
    :return: True если экспорт успешен
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Export to JSON failed: {e}")
        return False

def import_from_json(file_path: str) -> Optional[List[Dict]]:
    """
    Импорт данных из JSON файла
    :param file_path: Путь к файлу
    :return: Список словарей с данными или None
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Import from JSON failed: {e}")
        return None

def get_config(config_path: str = "config.json") -> Dict:
    """
    Загрузка конфигурации из JSON файла
    :param config_path: Путь к файлу конфигурации
    :return: Словарь с конфигурацией
    """
    default_config = {
        "database": "equipment.db",
        "backup_dir": "backups",
        "service_interval_days": 180,
        "default_user_role": "user"
    }
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            return {**default_config, **config}
    except FileNotFoundError:
        return default_config
    except json.JSONDecodeError:
        return default_config

def setup_logging(log_dir: str = "logs", 
                 log_level: str = "INFO", 
                 max_size: int = 1024*1024) -> None:
    """
    Настройка системы логирования
    :param log_dir: Директория для логов
    :param log_level: Уровень логирования
    :param max_size: Максимальный размер файла лога
    """
    import logging
    from logging.handlers import RotatingFileHandler
    
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, "app.log")
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler(
                log_file, maxBytes=max_size, backupCount=5
            ),
            logging.StreamHandler()
        ]
    )

def is_admin(user: Dict) -> bool:
    """
    Проверка, является ли пользователь администратором
    :param user: Словарь с данными пользователя
    :return: True если пользователь администратор
    """
    return user and user.get('role') == 'admin'

def generate_password(length: int = 12) -> str:
    """
    Генерация случайного пароля
    :param length: Длина пароля
    :return: Сгенерированный пароль
    """
    import random
    import string
    
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(chars) for _ in range(length))

def validate_email(email: str) -> bool:
    """
    Простая валидация email адреса
    :param email: Строка с email
    :return: True если email корректен
    """
    import re
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) is not None


def convert_cp1251_to_utf8(text: str) -> str:
    try:
        return text.encode('cp1251').decode('utf-8')
    except:
        return text