# core/auth.py
import sqlite3
from passlib.hash import pbkdf2_sha256
from database.db import db_connection
from typing import Optional, Dict


class AuthManager:
    def __init__(self):
        self.rounds = 29000  # Количество итераций для хэширования

    def create_user(self, username: str, password: str, role: str = "user") -> Dict:
        if not self._validate_password(password):
            raise ValueError("Password does not meet security requirements")

        with db_connection() as conn:
            try:
                hash = self._hash_password(password)
                print(f"Создание пользователя {username} с хэшем: {hash}")  # Отладочный вывод
                cursor = conn.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    (username, hash, role)
                )
                conn.commit()
                return self.get_user(cursor.lastrowid)
            except sqlite3.IntegrityError as e:
                raise ValueError(f"User {username} already exists") from e

    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        with db_connection() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE username = ?", 
                (username,)
            ).fetchone()

        if user:
            print(f"Найден пользователь: {user['username']}")
            print(f"Хэш в базе: {user['password_hash']}")
            print(f"Введённый пароль: {password}")
            verified = self._verify_password(password, user["password_hash"])
            print(f"Результат проверки: {verified}")
            if verified:
                return dict(user)
        else:
            print("Пользователь не найден")
        return None

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получение пользователя по ID"""
        with db_connection() as conn:
            row = conn.execute(
                "SELECT id, username, role, created_at FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()
            return dict(row) if row else None

    def update_user_role(self, user_id: int, new_role: str) -> None:
        """Обновление роли пользователя"""
        valid_roles = {"admin", "user"}
        if new_role not in valid_roles:
            raise ValueError(f"Invalid role. Allowed: {', '.join(valid_roles)}")

        with db_connection() as conn:
            conn.execute(
                "UPDATE users SET role = ? WHERE id = ?",
                (new_role, user_id)
            )
            conn.commit()

    def delete_user(self, user_id: int) -> bool:
        """Удаление пользователя по ID"""
        with db_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM users WHERE id = ?",
                (user_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def _hash_password(self, password: str) -> str:
        """Генерация безопасного хэша пароля"""
        return pbkdf2_sha256.using(rounds=self.rounds).hash(password)

    def _verify_password(self, password: str, hash: str) -> bool:
        """Проверка пароля против хэша"""
        return pbkdf2_sha256.verify(password, hash)

    # core/auth.py
    def _validate_password(self, password: str) -> bool:
        """Проверка сложности пароля"""
        if len(password) < 8:
            raise ValueError("Пароль должен содержать не менее 8 символов")
        if not any(c.isupper() for c in password):
            raise ValueError("Пароль должен содержать хотя бы одну заглавную букву")
        if not any(c.isdigit() for c in password):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")
        return True

    def list_users(self) -> list:
        """Получение списка всех пользователей"""
        with db_connection() as conn:
            cursor = conn.execute(
                "SELECT id, username, role, created_at FROM users"
            )
            return [dict(row) for row in cursor.fetchall()]
        
class MainWindow:
    def __init__(self, user):
        self.window = tk.Tk()
        self.window.title("Основное окно")
        tk.Label(self.window, text=f"Добро пожаловать, {user['username']}").pack(pady=20)
        tk.Button(self.window, text="Выйти", command=self.logout).pack(pady=20)

    def logout(self):
        self.window.destroy()
        auth_manager = AuthManager()
        login_window = LoginWindow(auth_manager)
        login_window.run()

    def run(self):
        self.window.mainloop()