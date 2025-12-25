"""
CRUD операции для работы с базой данных
"""
from datetime import datetime
from sqlalchemy import and_, or_, desc
from typing import Optional, List
import sys
import os

# Добавляем путь к корневой директории
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .models import Announcement, ManagerAction, ParsingLog, get_session
from utils.google_sheets import get_sheets_manager


class AnnouncementCRUD:
    """CRUD операции для объявлений"""

    @staticmethod
    def create(announcement_data: dict) -> Announcement:
        """Создать новое объявление"""
        session = get_session()
        try:
            announcement = Announcement(**announcement_data)
            session.add(announcement)
            session.commit()
            session.refresh(announcement)

            # Синхронизация с Google Sheets
            try:
                sheets_manager = get_sheets_manager()
                sheets_manager.add_announcement(announcement)
            except Exception as e:
                # Не прерываем работу при ошибке синхронизации
                from utils.logger import logger
                logger.error(f"Ошибка синхронизации с Google Sheets при создании: {e}")

            return announcement
        finally:
            session.close()

    @staticmethod
    def get_by_number(announcement_number: str) -> Optional[Announcement]:
        """Получить объявление по номеру"""
        session = get_session()
        try:
            return session.query(Announcement).filter(
                Announcement.announcement_number == announcement_number
            ).first()
        finally:
            session.close()

    @staticmethod
    def exists(announcement_number: str) -> bool:
        """Проверить существование объявления"""
        session = get_session()
        try:
            return session.query(Announcement).filter(
                Announcement.announcement_number == announcement_number
            ).count() > 0
        finally:
            session.close()

    @staticmethod
    def update_status(announcement_id: int, status: str, rejection_reason: str = None):
        """Обновить статус объявления"""
        session = get_session()
        try:
            announcement = session.query(Announcement).filter(
                Announcement.id == announcement_id
            ).first()

            if announcement:
                announcement.status = status
                announcement.response_at = datetime.utcnow()
                if rejection_reason:
                    announcement.rejection_reason = rejection_reason
                session.commit()
                session.refresh(announcement)

                # Синхронизация с Google Sheets
                try:
                    sheets_manager = get_sheets_manager()
                    sheets_manager.update_announcement(announcement)
                except Exception as e:
                    # Не прерываем работу при ошибке синхронизации
                    from utils.logger import logger
                    logger.error(f"Ошибка синхронизации с Google Sheets при обновлении: {e}")
        finally:
            session.close()

    @staticmethod
    def get_pending_for_manager(manager_id: int) -> List[Announcement]:
        """Получить ожидающие объявления для менеджера"""
        session = get_session()
        try:
            return session.query(Announcement).filter(
                and_(
                    Announcement.manager_id == manager_id,
                    Announcement.status == 'pending'
                )
            ).order_by(desc(Announcement.created_at)).all()
        finally:
            session.close()

    @staticmethod
    def get_all_by_status(status: str) -> List[Announcement]:
        """Получить все объявления по статусу"""
        session = get_session()
        try:
            return session.query(Announcement).filter(
                Announcement.status == status
            ).order_by(desc(Announcement.created_at)).all()
        finally:
            session.close()

    @staticmethod
    def get_all_for_report(start_date=None, end_date=None, manager_id=None) -> List[Announcement]:
        """Получить объявления для отчета с фильтрами"""
        session = get_session()
        try:
            query = session.query(Announcement)

            # Фильтр по дате
            if start_date:
                query = query.filter(Announcement.created_at >= start_date)
            if end_date:
                query = query.filter(Announcement.created_at <= end_date)

            # Фильтр по менеджеру
            if manager_id:
                query = query.filter(Announcement.manager_id == manager_id)

            return query.order_by(desc(Announcement.created_at)).all()
        finally:
            session.close()


class ManagerActionCRUD:
    """CRUD операции для действий менеджеров"""

    @staticmethod
    def create(action_data: dict) -> ManagerAction:
        """Создать запись о действии менеджера"""
        session = get_session()
        try:
            action = ManagerAction(**action_data)
            session.add(action)
            session.commit()
            session.refresh(action)
            return action
        finally:
            session.close()

    @staticmethod
    def get_by_announcement(announcement_id: int) -> List[ManagerAction]:
        """Получить все действия по объявлению"""
        session = get_session()
        try:
            return session.query(ManagerAction).filter(
                ManagerAction.announcement_id == announcement_id
            ).order_by(ManagerAction.created_at).all()
        finally:
            session.close()

    @staticmethod
    def get_by_manager(manager_id: int, limit: int = 10) -> List[ManagerAction]:
        """Получить последние действия менеджера"""
        session = get_session()
        try:
            return session.query(ManagerAction).filter(
                ManagerAction.manager_id == manager_id
            ).order_by(desc(ManagerAction.created_at)).limit(limit).all()
        finally:
            session.close()


class ParsingLogCRUD:
    """CRUD операции для логов парсинга"""

    @staticmethod
    def create() -> ParsingLog:
        """Создать новый лог парсинга"""
        session = get_session()
        try:
            log = ParsingLog(status='running')
            session.add(log)
            session.commit()
            session.refresh(log)
            return log
        finally:
            session.close()

    @staticmethod
    def update(log_id: int, **kwargs):
        """Обновить лог парсинга"""
        session = get_session()
        try:
            log = session.query(ParsingLog).filter(ParsingLog.id == log_id).first()
            if log:
                for key, value in kwargs.items():
                    setattr(log, key, value)
                session.commit()
        finally:
            session.close()

    @staticmethod
    def get_last() -> Optional[ParsingLog]:
        """Получить последний лог"""
        session = get_session()
        try:
            return session.query(ParsingLog).order_by(
                desc(ParsingLog.started_at)
            ).first()
        finally:
            session.close()
