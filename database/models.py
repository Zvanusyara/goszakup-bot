"""
Модели базы данных для системы мониторинга госзакупок
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import sys
import os

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


class Announcement(Base):
    """Объявления о госзакупках"""
    __tablename__ = 'announcements'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Данные объявления
    announcement_number = Column(String(100), unique=True, nullable=False, index=True)
    announcement_url = Column(String(500))

    # Данные организации
    organization_name = Column(String(500))
    organization_bin = Column(String(50))
    legal_address = Column(Text)
    region = Column(String(200), index=True)

    # Данные лота
    lot_name = Column(Text)
    lot_description = Column(Text)
    keyword_matched = Column(String(200))  # Ключевое слово, по которому найдено

    # Привязка к менеджеру
    manager_id = Column(Integer, index=True)
    manager_name = Column(String(200))

    # Статус обработки
    status = Column(String(50), default='pending', index=True)  # pending, accepted, rejected
    rejection_reason = Column(Text, nullable=True)

    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    response_at = Column(DateTime, nullable=True)  # Когда менеджер ответил

    # Уведомления
    notification_sent = Column(Boolean, default=False)
    admin_notified = Column(Boolean, default=False)

    # Связь с действиями
    actions = relationship("ManagerAction", back_populates="announcement", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Announcement {self.announcement_number} - {self.status}>"


class ManagerAction(Base):
    """История действий менеджеров"""
    __tablename__ = 'manager_actions'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Привязка к объявлению
    announcement_id = Column(Integer, ForeignKey('announcements.id'), nullable=False)
    announcement = relationship("Announcement", back_populates="actions")

    # Данные менеджера
    manager_id = Column(Integer, nullable=False)
    manager_name = Column(String(200))
    telegram_id = Column(Integer)

    # Действие
    action = Column(String(50), nullable=False)  # accepted, rejected, viewed
    comment = Column(Text, nullable=True)  # Причина отказа или комментарий

    # Временная метка
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ManagerAction {self.action} by {self.manager_name}>"


class ParsingLog(Base):
    """Лог парсинга для отслеживания работы системы"""
    __tablename__ = 'parsing_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Статистика парсинга
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    total_found = Column(Integer, default=0)  # Всего найдено объявлений
    new_added = Column(Integer, default=0)    # Новых добавлено
    duplicates = Column(Integer, default=0)    # Дубликатов пропущено

    # Статус
    status = Column(String(50), default='running')  # running, completed, failed
    error_message = Column(Text, nullable=True)

    def __repr__(self):
        return f"<ParsingLog {self.started_at} - {self.status}>"


def init_database():
    """Инициализация базы данных - создание всех таблиц"""
    Base.metadata.create_all(engine)
    print("✅ База данных инициализирована успешно!")
    print(f"📊 Созданы таблицы: {', '.join(Base.metadata.tables.keys())}")


def get_session():
    """Получить сессию для работы с БД"""
    return SessionLocal()


if __name__ == '__main__':
    # Инициализация БД при запуске этого файла
    init_database()
