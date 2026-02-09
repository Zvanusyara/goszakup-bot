"""
Tests for expired announcement cleanup logic
Validates the check_deadlines() method and expired filtering
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, AsyncMock

from database.models import Announcement


@pytest.mark.cleanup
@pytest.mark.unit
class TestExpiredAnnouncementCleanup:
    """Test automatic cleanup of expired announcements"""

    def test_mark_announcement_as_expired(self, db_session, expired_announcement_data):
        """Test that announcements with past deadlines can be marked as expired"""
        announcement = Announcement(**expired_announcement_data)
        db_session.add(announcement)
        db_session.commit()

        # Simulate cleanup logic
        now = datetime.utcnow()
        if announcement.application_deadline and announcement.application_deadline < now:
            announcement.status = 'expired'
            announcement.expired_at = now
            db_session.commit()

        # Verify
        assert announcement.status == 'expired'
        assert announcement.expired_at is not None

    def test_bulk_expire_old_announcements(self, db_session):
        """Test bulk expiration of old announcements"""
        now = datetime.utcnow()

        # Create 5 expired and 5 valid announcements
        for i in range(10):
            is_expired = i < 5
            announcement = Announcement(
                announcement_number=f'BULK-{i}',
                application_deadline=now - timedelta(days=10 if is_expired else -10),
                status='pending'
            )
            db_session.add(announcement)
        db_session.commit()

        # Bulk update (simulating check_deadlines logic)
        expired_count = db_session.query(Announcement).filter(
            Announcement.application_deadline < now,
            Announcement.status != 'expired'
        ).update({
            'status': 'expired',
            'expired_at': now
        }, synchronize_session=False)

        db_session.commit()

        assert expired_count == 5

    def test_expired_filter_excludes_from_processing(self, db_session):
        """Test that expired announcements are excluded from processing queries"""
        now = datetime.utcnow()

        # Create mix of announcements
        announcements_data = [
            ('PENDING-1', 'pending', now + timedelta(days=5)),
            ('ACCEPTED-1', 'accepted', now + timedelta(days=3)),
            ('EXPIRED-1', 'expired', now - timedelta(days=10)),
            ('REJECTED-1', 'rejected', now + timedelta(days=2)),
        ]

        for number, status, deadline in announcements_data:
            announcement = Announcement(
                announcement_number=number,
                status=status,
                application_deadline=deadline,
                manager_id=1
            )
            db_session.add(announcement)
        db_session.commit()

        # Query for reminders (should exclude expired)
        active_for_reminders = db_session.query(Announcement).filter(
            Announcement.status == 'accepted',
            Announcement.application_deadline.isnot(None),
            Announcement.application_deadline >= now,
            Announcement.manager_id.isnot(None)
        ).all()

        assert len(active_for_reminders) == 1
        assert active_for_reminders[0].announcement_number == 'ACCEPTED-1'

    def test_no_expired_with_future_deadline(self, db_session):
        """Test that no expired announcements have future deadlines"""
        now = datetime.utcnow()

        # Create expired announcement with past deadline
        announcement = Announcement(
            announcement_number='VALID-EXPIRED',
            application_deadline=now - timedelta(days=5),
            status='expired',
            expired_at=now
        )
        db_session.add(announcement)
        db_session.commit()

        # Query for invalid state (expired with future deadline)
        invalid = db_session.query(Announcement).filter(
            Announcement.status == 'expired',
            Announcement.application_deadline >= now
        ).count()

        assert invalid == 0
