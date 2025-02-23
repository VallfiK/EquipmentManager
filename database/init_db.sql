-- database/init_db.sql
PRAGMA foreign_keys = ON;

-- Таблица пользователей системы
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,       -- Логин (уникальный)
    password_hash TEXT NOT NULL,        -- Хэш пароля
    role TEXT CHECK(role IN ('admin', 'user')) NOT NULL DEFAULT 'user', -- Роль
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Таблица категорий оборудования
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,          -- Название категории
    description TEXT                    -- Описание категории
);

-- Таблица оборудования
CREATE TABLE IF NOT EXISTS equipment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                 -- Наименование оборудования
    category_id INTEGER NOT NULL,       -- Ссылка на категорию
    serial_number TEXT UNIQUE NOT NULL, -- Уникальный серийный номер
    status TEXT DEFAULT 'В работе' CHECK(status IN ('В работе', 'На ремонте', 'Списано')),
    purchase_date DATE NOT NULL,        -- Дата приобретения
    purchase_price REAL,                -- Стоимость приобретения
    last_service DATE,                  -- Дата последнего ТО
    next_service DATE,                  -- Дата следующего ТО
    notes TEXT,                         -- Произвольные заметки
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT
);


CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id INTEGER NOT NULL,      -- Ссылка на оборудование
    user_id INTEGER NOT NULL,           -- Пользователь, внесший изменение
    action_type TEXT NOT NULL,          -- Тип действия: create/update/delete
    action_details TEXT,                -- Детали изменения (JSON)
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (equipment_id) REFERENCES equipment(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);


CREATE INDEX IF NOT EXISTS idx_equipment_name ON equipment(name);
CREATE INDEX IF NOT EXISTS idx_equipment_serial ON equipment(serial_number);
CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp);


INSERT OR IGNORE INTO categories (name, description) VALUES
    ('Компьютеры', 'Персональные компьютеры и ноутбуки'),
    ('Серверы', 'Серверное оборудование'),
    ('Сетевое', 'Сетевые устройства и коммутаторы'),
    ('Периферия', 'Периферийные устройства');


INSERT OR IGNORE INTO users (username, password_hash, role) VALUES
    ('admin', '$pbkdf2-sha256$29000$AhCMj5b8Cq0VkFA8Jsi5gw$5cI4VPCVR0S0heFgdBxR1U3u6H5zqKJq5BZ/7JZzW5M', 'admin');