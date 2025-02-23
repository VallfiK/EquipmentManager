# core/reports.py
import sqlite3
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import cm
from datetime import datetime, timedelta
from database.db import db_connection
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from typing import List, Dict
import os

class ReportGenerator:
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_equipment_list_pdf(self, filters: Dict = None) -> str:
        """
        Генерация PDF отчета со списком оборудования
        :param filters: Словарь с параметрами фильтрации
        :return: Путь к созданному PDF файлу
        """
        filename = os.path.join(
            self.output_dir,
            f"equipment_list_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        )
        
        # Получаем данные
        data = self._get_equipment_data(filters)
        
        # Создаем PDF документ
        doc = SimpleDocTemplate(filename, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Заголовок
        elements.append(Paragraph("Отчет по оборудованию", styles['Title']))
        elements.append(Spacer(1, 0.5*cm))
        
        # Таблица с данными
        table_data = [["ID", "Наименование", "Категория", "Серийный номер", "Статус"]]
        table_data.extend(data)
        
        table = Table(table_data, colWidths=[1.5*cm, 6*cm, 4*cm, 4*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(table)
        doc.build(elements)
        return filename

    def generate_service_due_excel(self, days: int = 30) -> str:
        """
        Генерация Excel отчета по оборудованию с истекающим сроком ТО
        :param days: Количество дней для предупреждения
        :return: Путь к созданному Excel файлу
        """
        filename = os.path.join(
            self.output_dir,
            f"service_due_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        )
        
        with db_connection() as conn:
            query = '''
                SELECT 
                    e.id,
                    e.name,
                    e.serial_number,
                    c.name as category,
                    e.next_service
                FROM equipment e
                JOIN categories c ON e.category_id = c.id
                WHERE e.next_service <= ?
                    AND e.status = 'В работе'
                ORDER BY e.next_service
            '''
            due_date = datetime.now() + timedelta(days=days)
            df = pd.read_sql_query(query, conn, params=(due_date.strftime('%Y-%m-%d'),))
            
            # Форматирование данных
            df['next_service'] = pd.to_datetime(df['next_service']).dt.strftime('%d.%m.%Y')
            df.columns = ['ID', 'Наименование', 'Серийный номер', 'Категория', 'Дата ТО']
            
            # Сохранение в Excel
            writer = pd.ExcelWriter(filename, engine='xlsxwriter')
            df.to_excel(writer, index=False, sheet_name='Оборудование')
            
            # Настройка формата
            workbook = writer.book
            worksheet = writer.sheets['Оборудование']
            
            # Ширина колонок
            for i, col in enumerate(df.columns):
                width = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, width)
            
            # Заголовок
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })
            
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            writer.close()
            return filename

    def generate_full_inventory_report(self) -> str:
        """
        Генерация полного отчета по инвентаризации
        :return: Путь к созданному PDF файлу
        """
        filename = os.path.join(
            self.output_dir,
            f"full_inventory_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        )
        
        # Регистрация шрифта с поддержкой кириллицы
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfbase import pdfmetrics
        pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
        
        # Получаем данные
        categories = self._get_categories_data()
        equipment = self._get_equipment_data()
        
        # Создаем PDF документ
        doc = SimpleDocTemplate(filename, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Установка шрифта
        pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
        styles = getSampleStyleSheet()
        styles['Title'].fontName = 'DejaVuSans'
        styles['Heading2'].fontName = 'DejaVuSans'
        styles['Italic'].fontName = 'DejaVuSans'
        
        # Заголовок
        elements.append(Paragraph("Полный отчет по инвентаризации", styles['Title']))
        elements.append(Spacer(1, 0.5*cm))
        
        # Разделы по категориям
        for category in categories:
            # Заголовок категории
            elements.append(Paragraph(
                f"Категория: {category['name']}", 
                styles['Heading2']
            ))
            
            # Фильтруем оборудование по категории
            cat_equipment = [e for e in equipment if e[2] == category['name']]
            
            if not cat_equipment:
                elements.append(Paragraph("Оборудование отсутствует", styles['Italic']))
                continue
            
            # Таблица с оборудованием
            table_data = [["ID", "Наименование", "Серийный номер", "Статус"]]
            table_data.extend([[e[0], e[1], e[3], e[4]] for e in cat_equipment])
            
            table = Table(table_data, colWidths=[1.5*cm, 8*cm, 5*cm, 3*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),  # Используем DejaVuSans
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 1*cm))
        
        doc.build(elements)
        return filename

    def _get_equipment_data(self, filters: Dict = None) -> List[List]:
        """
        Получение данных об оборудовании для отчетов
        :param filters: Словарь с параметрами фильтрации
        :return: Список строк с данными
        """
        with db_connection() as conn:
            query = '''
                SELECT 
                    e.id,
                    e.name,
                    c.name as category,
                    e.serial_number,
                    e.status
                FROM equipment e
                LEFT JOIN categories c ON e.category_id = c.id
            '''
            params = []
            
            if filters:
                query += " WHERE 1=1"
                if 'category_id' in filters:
                    query += " AND e.category_id = ?"
                    params.append(filters['category_id'])
                
                if 'status' in filters:
                    query += " AND e.status = ?"
                    params.append(filters['status'])
            
            query += " ORDER BY e.name"
            cursor = conn.execute(query, params)
            return [list(row) for row in cursor.fetchall()]

    def _get_categories_data(self) -> List[Dict]:
        """
        Получение данных о категориях
        :return: Список словарей с данными категорий
        """
        with db_connection() as conn:
            cursor = conn.execute('SELECT id, name FROM categories ORDER BY name')
            return [dict(row) for row in cursor.fetchall()]