# database/db.py
import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime
import sys
# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if os.name == 'nt':
    os.system('chcp 65001 > nul')


# Конфигурация базы данных
DATABASE = 'equipment.db'
SQL_INIT_FILE = os.path.join(os.path.dirname(__file__), 'init_db.sql')

@contextmanager
def db_connection():
    conn = sqlite3.connect(DATABASE, timeout=10)  # Таймаут 10 секунд
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()
        
def init_db(force=False):
    """Инициализация структуры базы данных"""
    with db_connection() as conn:
        if force:
            conn.executescript("""
                DROP TABLE IF EXISTS history;
                DROP TABLE IF EXISTS equipment;
                DROP TABLE IF EXISTS categories;
                DROP TABLE IF EXISTS users;
            """)
            print("Таблицы удалены")
        
        tables_exist = conn.execute("""
            SELECT count(*) FROM sqlite_master 
            WHERE type='table' AND name IN ('users', 'equipment')
        """).fetchone()[0] >= 2
        
        if not tables_exist:
            print("Initializing database...")
            with open(SQL_INIT_FILE, 'r', encoding='utf-8') as f:
                conn.executescript(f.read())
                print("Скрипт инициализации выполнен")
            create_test_admin()
            print("Database initialized successfully")


def create_test_admin():
    """Создание тестового пользователя администратора"""
    from core.auth import AuthManager
    auth = AuthManager()
    
    try:
        with db_connection() as conn:
            # Удаляем пользователя, если он существует
            conn.execute("DELETE FROM users WHERE username = ?", ("admin",))
            conn.commit()
            print("Старый пользователь 'admin' удалён")
                
        # Создаем пользователя заново
        print("Создание пользователя 'admin'...")
        auth.create_user(
            username="admin",
            password="Admin123!",
            role="admin"
        )
        print("Пользователь 'admin' успешно создан")
        
        # Проверка аутентификации сразу после создания
        test_user = auth.authenticate("admin", "Admin123!")
        if test_user:
            print("Проверка: Аутентификация прошла успешно")
        else:
            print("Проверка: Ошибка аутентификации")
    except Exception as e:
        print(f"Ошибка при создании пользователя: {e}")

def backup_database():
    """Создание резервной копии базы данных"""
    backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M')}.db"
    with db_connection() as src:
        with sqlite3.connect(backup_name) as dst:
            src.backup(dst)
    return backup_name

if __name__ == "__main__":
    # Инициализация БД при прямом запуске
    init_db(force=True)
    print(f"Database {DATABASE} created with test data")