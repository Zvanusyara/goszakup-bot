"""
Unit tests for database models
Tests model definitions, fields, and relationships
"""
import pytest
from datetime import datetime, timedelta
import json

from database.models import Announcement, ManagerAction, ParsingLog


@pytest.mark.database
@pytest.mark.unit
class TestAnnouncementModel:
    """Test Announcement model"""

    def test_announcement_creation(self, db_session, sample_announcement_data):
        """Test creating a basic announcement"""
        announcement = Announcement(**sample_announcement_data)
        db_session.add(announcement)
        db_session.commit()

        assert announcement.id is not None
        assert announcement.announcement_number == 'TEST-2024-001'
        assert announcement.status == 'pending'
        assert announcement.manager_id == 1
        assert announcement.region == 'г. Алматы'

    def test_announcement_has_expired_at_field(self, db_session, sample_announcement_data):
        """Test that expired_at field exists in Announcement model"""
        announcement = Announcement(**sample_announcement_data)
        db_session.add(announcement)
        db_session.commit()

        # Check that expired_at field exists and is None by default
        assert hasattr(announcement, 'expired_at')
        assert announcement.expired_at is None

    def test_announcement_expired_at_can_be_set(self, db_session, sample_announcement_data):
        """Test setting expired_at timestamp"""
        sample_announcement_data['status'] = 'expired'
        sample_announcement_data['expired_at'] = datetime.utcnow()

        announcement = Announcement(**sample_announcement_data)
        db_session.add(announcement)
        db_session.commit()

        assert announcement.expired_at is not None
        assert announcement.status == 'expired'

    def test_announcement_with_lots_json(self, db_session, sample_announcement_with_lots):
        """Test announcement with lots stored as JSON"""
        # Convert lots to JSON string
        lots_data = sample_announcement_with_lots.pop('lots')
        sample_announcement_with_lots['lots'] = json.dumps(lots_data, ensure_ascii=False)

        announcement = Announcement(**sample_announcement_with_lots)
        db_session.add(announcement)
        db_session.commit()

        # Verify lots are stored as JSON string
        assert announcement.lots is not None
        assert isinstance(announcement.lots, str)

        # Verify we can deserialize
        deserialized = json.loads(announcement.lots)
        assert len(deserialized) == 2
        assert deserialized[0]['name'] == 'Lot 1 Name'

    def test_announcement_timestamps(self, db_session, sample_announcement_data):
        """Test automatic timestamp creation"""
        before = datetime.utcnow()
        announcement = Announcement(**sample_announcement_data)
        db_session.add(announcement)
        db_session.commit()
        after = datetime.utcnow()

        assert announcement.created_at is not None
        assert before <= announcement.created_at <= after
        assert announcement.updated_at is not None
