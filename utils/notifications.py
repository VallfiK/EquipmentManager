# utils/notifications.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import sqlite3
from database.db import db_connection
from utils.helpers import format_date, show_info_message
import logging

logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self, config: Dict):
        self.config = config
        self.smtp_config = config.get('smtp', {})
        self.notification_settings = config.get('notifications', {})

    def check_service_due(self, days: int = 7) -> List[Dict]:
        """
        Проверка оборудования с истекающим сроком ТО
        :param days: Количество дней для предупреждения
        :return: Список оборудования с истекающим сроком ТО
        """
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

    def send_email_notification(self, to: str, subject: str, body: str) -> bool:
        """
        Отправка email уведомления
        :param to: Адрес получателя
        :param subject: Тема письма
        :param body: Текст письма
        :return: True если отправка успешна
        """
        if not self.smtp_config:
            logger.warning("SMTP configuration not found")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config.get('from')
            msg['To'] = to
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'html'))

            with smtplib.SMTP(
                self.smtp_config.get('host'), 
                self.smtp_config.get('port')
            ) as server:
                if self.smtp_config.get('tls'):
                    server.starttls()
                
                server.login(
                    self.smtp_config.get('user'),
                    self.smtp_config.get('password')
                )
                server.send_message(msg)
            
            logger.info(f"Email sent to {to}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def notify_service_due(self) -> None:
        """
        Отправка уведомлений о приближающемся ТО
        """
        if not self.notification_settings.get('enabled', False):
            return

        equipment_due = self.check_service_due(
            self.notification_settings.get('days_before', 7)
        )
        
        if not equipment_due:
            return

        # Формирование текста уведомления
        subject = "Уведомление о приближающемся ТО"
        body = "<h2>Оборудование с истекающим сроком ТО:</h2><ul>"
        
        for item in equipment_due:
            service_date = format_date(item['next_service'], to_fmt='%d.%m.%Y')
            body += f"<li>{item['name']} ({item['category']}), серийный номер: {item['serial_number']}, дата ТО: {service_date}</li>"
        
        body += "</ul>"

        # Отправка уведомлений
        recipients = self.notification_settings.get('recipients', [])
        for recipient in recipients:
            self.send_email_notification(recipient, subject, body)

    def show_service_due_notification(self, parent) -> None:
        """
        Показ уведомления о приближающемся ТО в интерфейсе
        :param parent: Родительское окно
        """
        equipment_due = self.check_service_due(
            self.notification_settings.get('days_before', 7)
        )
        
        if equipment_due:
            message = "Следующее оборудование требует ТО:\n\n"
            for item in equipment_due:
                service_date = format_date(item['next_service'], to_fmt='%d.%m.%Y')
                message += f"- {item['name']} ({item['category']}), серийный номер: {item['serial_number']}, дата ТО: {service_date}\n"
            
            show_info_message(parent, "Уведомление о ТО", message)

    def log_notification(self, equipment_id: int, 
                        notification_type: str, 
                        status: str) -> None:
        """
        Логирование отправленных уведомлений
        :param equipment_id: ID оборудования
        :param notification_type: Тип уведомления (email, ui)
        :param status: Статус отправки (success, failed)
        """
        with db_connection() as conn:
            conn.execute('''
                INSERT INTO notifications (
                    equipment_id,
                    type,
                    status,
                    timestamp
                ) VALUES (?, ?, ?, ?)
            ''', (
                equipment_id,
                notification_type,
                status,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            conn.commit()

def setup_notifications(config: Dict) -> NotificationManager:
    """
    Инициализация менеджера уведомлений
    :param config: Конфигурация приложения
    :return: Экземпляр NotificationManager
    """
    return NotificationManager(config)