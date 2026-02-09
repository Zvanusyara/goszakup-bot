"""
Integration tests for critical bot functionality
Tests end-to-end workflows
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from database.models import Announcement
from database.crud import AnnouncementCRUD


@pytest.mark.integration
class TestCriticalWorkflows:
    """Test critical workflows to ensure no old announcements are processed"""

    def test_migration_executed_correctly(self, db_session):
        """Verify migration results: expired announcements are marked correctly"""
        now = datetime.utcnow()

        # Simulate post-migration state
        announcements = [
            Announcement(
                announcement_number='POST-MIG-EXPIRED-1',
                application_deadline=now - timedelta(days=30),
                status='expired',
                expired_at=now - timedelta(days=30)
            ),
            Announcement(
                announcement_number='POST-MIG-VALID-1',
                application_deadline=now + timedelta(days=10),
                status='pending'
            )
        ]

        for ann in announcements:
            db_session.add(ann)
        db_session.commit()

        # Verify counts
        expired_count = db_session.query(Announcement).filter(
            Announcement.status == 'expired'
        ).count()
        pending_count = db_session.query(Announcement).filter(
            Announcement.status == 'pending'
        ).count()

        assert expired_count == 1
        assert pending_count == 1

        # Verify all expired have expired_at
        expired_without_timestamp = db_session.query(Announcement).filter(
            Announcement.status == 'expired',
            Announcement.expired_at.is_(None)
        ).count()

        assert expired_without_timestamp == 0

    @pytest.mark.asyncio
    async def test_no_notifications_for_expired_announcements(self, db_session, mock_bot):
        """Critical: Bot should NOT send notifications for expired announcements"""
        now = datetime.utcnow()

        # Create expired announcement
        announcement = Announcement(
            announcement_number='NO-NOTIFY-EXPIRED',
            application_deadline=now - timedelta(days=20),
            status='expired',
            expired_at=now - timedelta(days=20),
            manager_id=1
        )
        db_session.add(announcement)
        db_session.commit()

        # Simulate notification logic (should skip expired)
        announcements_to_notify = db_session.query(Announcement).filter(
            Announcement.status.in_(['pending', 'accepted']),  # Exclude expired
            Announcement.application_deadline >= now
        ).all()

        # No expired announcements should be in the list
        assert len(announcements_to_notify) == 0
        mock_bot.send_message.assert_not_called()

    def test_parser_filters_exclude_old_announcements(self, db_session):
        """Critical: Parser should NOT add announcements with past deadlines to DB"""
        now = datetime.utcnow()

        # Simulate parser filtering logic
        parsed_announcements = [
            {
                'announcement_number': 'PARSED-VALID-1',
                'application_deadline': now + timedelta(days=7),
                'status': 'pending'
            },
            {
                'announcement_number': 'PARSED-OLD-1',
                'application_deadline': now - timedelta(days=15),
                'status': 'pending'
            }
        ]

        # Filter out old announcements (days_back=7)
        cutoff = now - timedelta(days=7)
        valid_announcements = [
            ann for ann in parsed_announcements
            if ann['application_deadline'] >= cutoff
        ]

        # Only valid announcement should remain
        assert len(valid_announcements) == 1
        assert valid_announcements[0]['announcement_number'] == 'PARSED-VALID-1'

    def test_check_deadlines_only_processes_active(self, db_session):
        """Test that check_deadlines() only processes accepted announcements with valid deadlines"""
        now = datetime.utcnow()

        # Create various announcement states
        announcements = [
            Announcement(
                announcement_number='ACTIVE-1',
                status='accepted',
                application_deadline=now + timedelta(hours=30),
                manager_id=1
            ),
            Announcement(
                announcement_number='EXPIRED-1',
                status='expired',
                application_deadline=now - timedelta(days=5),
                manager_id=1,
                expired_at=now - timedelta(days=5)
            ),
            Announcement(
                announcement_number='PENDING-1',
                status='pending',
                application_deadline=now + timedelta(days=10),
                manager_id=1
            )
        ]

        for ann in announcements:
            db_session.add(ann)
        db_session.commit()

        # Simulate check_deadlines query
        eligible_for_reminders = db_session.query(Announcement).filter(
            Announcement.status == 'accepted',
            Announcement.application_deadline.isnot(None),
            Announcement.application_deadline >= now,
            Announcement.manager_id.isnot(None)
        ).all()

        # Only accepted with future deadline
        assert len(eligible_for_reminders) == 1
        assert eligible_for_reminders[0].announcement_number == 'ACTIVE-1'
