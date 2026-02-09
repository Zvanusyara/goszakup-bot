"""
Pytest configuration and shared fixtures for goszakup-bot tests
"""
import pytest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import Base, engine, SessionLocal, Announcement, ManagerAction, ParsingLog
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="session")
def test_database_url():
    """Use in-memory SQLite database for tests"""
    return "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_session(test_database_url):
    """
    Create a fresh database session for each test.
    Uses in-memory SQLite for fast, isolated tests.
    """
    # Create test engine
    test_engine = create_engine(test_database_url, echo=False)

    # Create all tables
    Base.metadata.create_all(test_engine)

    # Create session
    TestSessionLocal = sessionmaker(bind=test_engine)
    session = TestSessionLocal()

    yield session

    # Cleanup
    session.close()
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture
def sample_announcement_data():
    """Sample announcement data for testing"""
    return {
        'announcement_number': 'TEST-2024-001',
        'announcement_url': 'https://goszakup.gov.kz/test/001',
        'organization_name': 'Test Organization',
        'organization_bin': '123456789012',
        'legal_address': 'г. Алматы, ул. Тестовая, 1',
        'region': 'г. Алматы',
        'lot_name': 'Test Lot',
        'lot_description': 'Test Description',
        'keyword_matched': 'медицинские изделия',
        'application_deadline': datetime.utcnow() + timedelta(days=7),
        'procurement_method': 'Тендер',
        'manager_id': 1,
        'manager_name': 'Test Manager',
        'status': 'pending'
    }


@pytest.fixture
def sample_announcement_with_lots():
    """Sample announcement with multiple lots"""
    return {
        'announcement_number': 'TEST-2024-002',
        'announcement_url': 'https://goszakup.gov.kz/test/002',
        'organization_name': 'Test Organization Multi',
        'organization_bin': '987654321098',
        'legal_address': 'г. Астана, пр. Мира, 10',
        'region': 'г. Астана',
        'lots': [
            {
                'number': 1,
                'name': 'Lot 1 Name',
                'description': 'Lot 1 Description',
                'keyword': 'медицинские изделия'
            },
            {
                'number': 2,
                'name': 'Lot 2 Name',
                'description': 'Lot 2 Description',
                'keyword': 'аренда'
            }
        ],
        'keyword_matched': 'медицинские изделия, аренда',
        'application_deadline': datetime.utcnow() + timedelta(days=5),
        'procurement_method': 'Открытый конкурс',
        'manager_id': 2,
        'manager_name': 'Manager Two',
        'status': 'pending'
    }


@pytest.fixture
def expired_announcement_data():
    """Announcement with expired deadline (in the past)"""
    return {
        'announcement_number': 'EXPIRED-2024-001',
        'announcement_url': 'https://goszakup.gov.kz/expired/001',
        'organization_name': 'Expired Organization',
        'organization_bin': '111222333444',
        'legal_address': 'г. Караганда, ул. Старая, 99',
        'region': 'Карагандинская область',
        'lot_name': 'Expired Lot',
        'lot_description': 'This lot has expired',
        'keyword_matched': 'старое',
        'application_deadline': datetime.utcnow() - timedelta(days=10),  # 10 days ago
        'procurement_method': 'Тендер',
        'manager_id': 1,
        'manager_name': 'Test Manager',
        'status': 'pending'  # Will be marked as expired by cleanup logic
    }


@pytest.fixture
def mock_bot():
    """Mock Telegram Bot instance"""
    bot = AsyncMock()
    bot.send_message = AsyncMock(return_value=Mock(message_id=123))
    bot.answer_callback_query = AsyncMock()
    bot.edit_message_text = AsyncMock()
    bot.edit_message_reply_markup = AsyncMock()
    return bot


@pytest.fixture
def mock_message():
    """Mock Telegram Message object"""
    message = Mock()
    message.answer = AsyncMock()
    message.from_user = Mock()
    message.from_user.id = 12345
    message.from_user.username = "test_user"
    message.chat = Mock()
    message.chat.id = 12345
    return message


@pytest.fixture
def mock_callback_query():
    """Mock Telegram CallbackQuery object"""
    callback = Mock()
    callback.answer = AsyncMock()
    callback.message = Mock()
    callback.message.edit_text = AsyncMock()
    callback.message.edit_reply_markup = AsyncMock()
    callback.from_user = Mock()
    callback.from_user.id = 12345
    callback.data = "test_data"
    return callback


@pytest.fixture
def mock_google_sheets():
    """Mock GoogleSheetsManager"""
    sheets = MagicMock()
    sheets.enabled = True
    sheets.add_announcement = MagicMock(return_value=True)
    sheets.update_announcement = MagicMock(return_value=True)
    sheets.retry_initialization = MagicMock(return_value=True)
    return sheets


@pytest.fixture
def mock_parser():
    """Mock GoszakupParser"""
    parser = MagicMock()
    parser.search_lots = MagicMock(return_value=[])
    parser.get_customer_address = MagicMock(return_value='Test Address')
    return parser


@pytest.fixture
def temp_test_db():
    """Create temporary database file for integration tests"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test_goszakup.db')
    db_url = f'sqlite:///{db_path}'

    yield db_url

    # Cleanup
    shutil.rmtree(temp_dir)
