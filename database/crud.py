"""
CRUD операции для работы с базой данных
"""
from datetime import datetime, timezone
from sqlalchemy import and_, or_, desc
from typing import Optional, List
import json
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
            # Сериализуем массив лотов в JSON, если есть
            data = announcement_data.copy()
            if 'lots' in data and isinstance(data['lots'], list):
                data['lots'] = json.dumps(data['lots'], ensure_ascii=False)

            announcement = Announcement(**data)
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
                announcement.response_at = datetime.now(timezone.utc)
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

    @staticmethod
    def get_accepted_for_manager(manager_id: int) -> List[Announcement]:
        """Получить принятые объявления для менеджера (в работе)"""
        session = get_session()
        try:
            return session.query(Announcement).filter(
                and_(
                    Announcement.manager_id == manager_id,
                    Announcement.status == 'accepted'
                )
            ).order_by(desc(Announcement.created_at)).all()
        finally:
            session.close()

    @staticmethod
    def mark_as_processed(announcement_id: int):
        """Отметить объявление как обработанное"""
        session = get_session()
        try:
            announcement = session.query(Announcement).filter(
                Announcement.id == announcement_id
            ).first()

            if announcement:
                announcement.is_processed = True
                session.commit()
                session.refresh(announcement)

                # Синхронизация с Google Sheets
                try:
                    sheets_manager = get_sheets_manager()
                    sheets_manager.update_announcement(announcement)
                except Exception as e:
                    from utils.logger import logger
                    logger.error(f"Ошибка синхронизации с Google Sheets при обработке: {e}")
        finally:
            session.close()

    @staticmethod
    def get_manager_statistics(manager_id: int) -> dict:
        """
        Получить статистику для конкретного менеджера

        Args:
            manager_id: ID менеджера

        Returns:
            Словарь со статистикой: total, pending, accepted, processed, rejected,
            acceptance_rate, processing_rate, avg_response_time
        """
        session = get_session()
        try:
            from datetime import timedelta

            # Общее количество
            total = session.query(Announcement).filter(
                Announcement.manager_id == manager_id
            ).count()

            # По статусам
            pending = session.query(Announcement).filter(
                Announcement.manager_id == manager_id,
                Announcement.status == 'pending'
            ).count()

            accepted = session.query(Announcement).filter(
                Announcement.manager_id == manager_id,
                Announcement.status == 'accepted'
            ).count()

            processed = session.query(Announcement).filter(
                Announcement.manager_id == manager_id,
                Announcement.status == 'accepted',
                Announcement.is_processed == True
            ).count()

            rejected = session.query(Announcement).filter(
                Announcement.manager_id == manager_id,
                Announcement.status == 'rejected'
            ).count()

            # Процент принятия (accepted / (accepted + rejected))
            total_responded = accepted + rejected
            acceptance_rate = (accepted / total_responded * 100) if total_responded > 0 else 0

            # Процент обработки (processed / accepted)
            processing_rate = (processed / accepted * 100) if accepted > 0 else 0

            # Среднее время реакции (для объявлений с ответом)
            announcements_with_response = session.query(Announcement).filter(
                Announcement.manager_id == manager_id,
                Announcement.response_at.isnot(None)
            ).all()

            if announcements_with_response:
                total_response_time = sum([
                    (ann.response_at - ann.created_at).total_seconds() / 3600
                    for ann in announcements_with_response
                ])
                avg_response_time = total_response_time / len(announcements_with_response)
            else:
                avg_response_time = 0

            return {
                'total': total,
                'pending': pending,
                'accepted': accepted,
                'processed': processed,
                'rejected': rejected,
                'acceptance_rate': round(acceptance_rate, 1),
                'processing_rate': round(processing_rate, 1),
                'avg_response_time': round(avg_response_time, 1)
            }

        finally:
            session.close()

    @staticmethod
    def get_problem_announcements(manager_id: int) -> dict:
        """
        Получить проблемные объявления менеджера

        Args:
            manager_id: ID менеджера

        Returns:
            Словарь с ключами pending_24h (список объявлений pending > 24ч)
            и accepted_48h (список объявлений accepted не обработаны > 48ч)
        """
        session = get_session()
        try:
            from datetime import timedelta

            now = datetime.now(timezone.utc)

            # Pending более 24 часов
            pending_24h_threshold = now - timedelta(hours=24)
            pending_24h = session.query(Announcement).filter(
                and_(
                    Announcement.manager_id == manager_id,
                    Announcement.status == 'pending',
                    Announcement.created_at < pending_24h_threshold
                )
            ).order_by(Announcement.created_at).all()

            # Accepted но не обработаны более 48 часов
            accepted_48h_threshold = now - timedelta(hours=48)
            accepted_48h = session.query(Announcement).filter(
                and_(
                    Announcement.manager_id == manager_id,
                    Announcement.status == 'accepted',
                    Announcement.is_processed == False,
                    Announcement.response_at < accepted_48h_threshold
                )
            ).order_by(Announcement.response_at).all()

            return {
                'pending_24h': pending_24h,
                'accepted_48h': accepted_48h
            }

        finally:
            session.close()

    @staticmethod
    def get_active_announcements(manager_id: int) -> List[Announcement]:
        """
        Получить активные объявления менеджера (accepted и не обработаны)

        Args:
            manager_id: ID менеджера

        Returns:
            Список активных объявлений
        """
        session = get_session()
        try:
            return session.query(Announcement).filter(
                and_(
                    Announcement.manager_id == manager_id,
                    Announcement.status == 'accepted',
                    Announcement.is_processed == False
                )
            ).order_by(Announcement.created_at).all()

        finally:
            session.close()

    @staticmethod
    def get_accepted_with_valid_deadline() -> List[Announcement]:
        """
        Получить все принятые объявления, срок окончания которых еще не наступил
        (для координатора)

        Returns:
            Список объявлений со статусом accepted и deadline_at > now
        """
        session = get_session()
        try:
            now = datetime.now(timezone.utc)
            return session.query(Announcement).filter(
                and_(
                    Announcement.status == 'accepted',
                    Announcement.deadline_at > now
                )
            ).order_by(desc(Announcement.deadline_at)).all()

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
