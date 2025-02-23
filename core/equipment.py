import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from database.db import db_connection
import json
import logging

logger = logging.getLogger(__name__)

class EquipmentManager:
    def __init__(self):
        self.status_options = ['В работе', 'На ремонте', 'Списано']

    def add_equipment(self, equipment_data: Dict, user_id: int) -> Dict:
        """Добавление нового оборудования"""
        logger.debug(f"Добавление оборудования: {equipment_data}")
        
        try:
            with db_connection() as conn:
                conn.execute("BEGIN TRANSACTION")
                cursor = conn.execute('''
                    INSERT INTO equipment (
                        name, 
                        category_id,
                        serial_number,
                        status,
                        purchase_date,
                        purchase_price,
                        last_service,
                        next_service,
                        notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    equipment_data['name'],
                    equipment_data['category_id'],
                    equipment_data['serial_number'],
                    equipment_data.get('status', 'В работе'),
                    equipment_data['purchase_date'],
                    equipment_data.get('purchase_price'),
                    equipment_data.get('last_service'),
                    equipment_data.get('next_service'),
                    equipment_data.get('notes', '')
                ))
                
                equipment_id = cursor.lastrowid
                if not equipment_id:
                    raise ValueError("Не удалось получить ID добавленного оборудования")

                self._log_history(conn, equipment_id, user_id, 'create', equipment_data)
                conn.commit()
                return self.get_equipment(equipment_id)
            
        except sqlite3.IntegrityError as e:
            conn.rollback()
            logger.error(f"Ошибка целостности данных: {e}")
            raise ValueError("Серийный номер должен быть уникальным") from e
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка при добавлении оборудования: {e}")
            raise

    def update_equipment(self, equipment_id: int, update_data: Dict, user_id: int) -> Dict:
        """
        Обновление данных оборудования
        :param equipment_id: ID обновляемого оборудования
        :param update_data: Словарь с обновляемыми полями
        :param user_id: ID пользователя, выполняющего операцию
        :return: Обновленная запись оборудования
        """
        self._validate_update_data(update_data)  # Вызов исправленного метода
        
        with db_connection() as conn:
            original_data = self.get_equipment(equipment_id)
            if not original_data:
                raise ValueError("Оборудование не найдено")
            
            conn.execute('''
                UPDATE equipment SET
                    name = COALESCE(?, name),
                    category_id = COALESCE(?, category_id),
                    status = COALESCE(?, status),
                    purchase_price = COALESCE(?, purchase_price),
                    last_service = COALESCE(?, last_service),
                    next_service = COALESCE(?, next_service),
                    notes = COALESCE(?, notes)
                WHERE id = ?
            ''', (
                update_data.get('name'),
                update_data.get('category_id'),
                update_data.get('status'),
                update_data.get('purchase_price'),
                update_data.get('last_service'),
                update_data.get('next_service'),
                update_data.get('notes'),
                equipment_id
            ))
            
            self._log_history(conn, equipment_id, user_id, 'update', update_data)
            conn.commit()
            return self.get_equipment(equipment_id)

    def delete_equipment(self, equipment_id: int, user_id: int) -> bool:
        """
        Удаление оборудования
        :param equipment_id: ID удаляемого оборудования
        :param user_id: ID пользователя, выполняющего операцию
        :return: True если удаление успешно
        """
        with db_connection() as conn:
            deleted = conn.execute('DELETE FROM equipment WHERE id = ?', (equipment_id,)).rowcount
            if deleted:
                self._log_history(conn, equipment_id, user_id, 'delete')  # Исправлено: передаём conn
                conn.commit()
            return deleted > 0

    def get_equipment(self, equipment_id: int) -> Optional[Dict]:
        """Получение данных оборудования по ID"""
        logger.debug(f"Получение оборудования по ID: {equipment_id}")
        
        try:
            with db_connection() as conn:
                cursor = conn.execute('''
                    SELECT 
                        e.*,
                        c.name as category_name,
                        c.description as category_description
                    FROM equipment e
                    LEFT JOIN categories c 
                        ON e.category_id = c.id 
                        AND c.id IS NOT NULL
                    WHERE e.id = ?
                ''', (equipment_id,))
                
                row = cursor.fetchone()
                if row:
                    columns = [column[0] for column in cursor.description]
                    equipment_dict = dict(zip(columns, row))
                    logger.debug(f"Найдено оборудование: {equipment_dict}")
                    return equipment_dict
                else:
                    logger.warning(f"Оборудование с ID {equipment_id} не найдено")
                    return None
        except Exception as e:
            logger.error(f"Ошибка при получении оборудования: {e}")
            raise

    def search_equipment(self, filters: Dict) -> List[Dict]:
        """Поиск оборудования с фильтрами"""
        query = '''
            SELECT 
                e.id,
                e.name,
                c.name as category,  
                e.serial_number,     
                e.status,            
                e.next_service
            FROM equipment e
            LEFT JOIN categories c ON e.category_id = c.id
            WHERE 1=1
        '''
        params = []
        
        if filters.get('category_id') is not None:
            query += " AND e.category_id = ?"
            params.append(filters['category_id'])
        
        if filters.get('status'):
            query += " AND e.status = ?"
            params.append(filters['status'])
            
        query += " ORDER BY e.name"
        
        with db_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_service_due(self, days: int = 30) -> List[Dict]:
        """Получение оборудования с ближайшим сроком ТО"""
        due_date = datetime.now() + timedelta(days=days)
        with db_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    e.id,
                    e.name,
                    e.serial_number,
                    e.next_service,
                    c.name as category
                FROM equipment e
                JOIN categories c ON e.category_id = c.id
                WHERE e.next_service <= ? 
                    AND e.status = 'В работе'
                ORDER BY e.next_service
            ''', (due_date.strftime('%Y-%m-%d'),))
            return [dict(row) for row in cursor.fetchall()]

    def _log_history(self, conn, equipment_id: int, user_id: int, action_type: str, details: Dict = None) -> None:
        """Логирование изменений в истории"""
        try:
            conn.execute('''
                INSERT INTO history (
                    equipment_id,
                    user_id,
                    action_type,
                    action_details
                ) VALUES (?, ?, ?, ?)
            ''', (
                equipment_id,
                user_id,
                action_type,
                json.dumps(details) if details else None
            ))
        except Exception as e:
            logger.error(f"Ошибка при логировании истории: {e}")
            raise

    def _validate_equipment_data(self, data: Dict) -> None:
        """Валидация данных при создании оборудования"""
        required_fields = ['name', 'category_id', 'serial_number', 'purchase_date']
        for field in required_fields:
            if field not in data or data[field] is None:
                raise ValueError(f"Необходимо поле {field}")
                
        if data.get('status') and data['status'] not in self.status_options:
            raise ValueError(f"Недопустимый статус. Допустимые значения: {', '.join(self.status_options)}")
        
        if not self._category_exists(data['category_id']):
            raise ValueError("Указана несуществующая категория")

    def _validate_update_data(self, data: Dict) -> None:
        """Валидация данных при обновлении оборудования"""
        # Проверяем только те поля, которые переданы
        if 'status' in data and data['status'] and data['status'] not in self.status_options:
            raise ValueError(f"Недопустимый статус. Допустимые значения: {', '.join(self.status_options)}")
        
        if 'category_id' in data and data['category_id'] is not None:
            if not self._category_exists(data['category_id']):
                raise ValueError("Указана несуществующая категория")
        
        # Дополнительная проверка формата дат, если они есть
        for date_field in ['purchase_date', 'last_service', 'next_service']:
            if date_field in data and data[date_field]:
                try:
                    datetime.strptime(data[date_field], '%Y-%m-%d')
                except ValueError:
                    raise ValueError(f"Неверный формат даты в поле {date_field}. Используйте YYYY-MM-DD")

    def _category_exists(self, category_id: int) -> bool:
        """Проверка существования категории"""
        with db_connection() as conn:
            return conn.execute(
                'SELECT 1 FROM categories WHERE id = ?', 
                (category_id,)
            ).fetchone() is not None

    def get_history(self, equipment_id: int) -> List[Dict]:
        """Получение истории изменений оборудования"""
        with db_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    h.timestamp,
                    u.username,
                    h.action_type,
                    h.action_details
                FROM history h
                JOIN users u ON h.user_id = u.id
                WHERE h.equipment_id = ?
                ORDER BY h.timestamp DESC
            ''', (equipment_id,))
            return [dict(row) for row in cursor.fetchall()]